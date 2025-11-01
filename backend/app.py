from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
from werkzeug.utils import secure_filename
import os
import asyncio
from dotenv import load_dotenv
from services.rag_service import RAGService
from services.llm_service import EmbeddingService, ChatService
from services.citation_service import CitationService
from services.url_selector import URLSelector
from services.groq_service import GroqService
import logging
from datetime import datetime
import uuid
from typing import List, Dict
from services.document_pipeline import DocumentPipeline

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import web crawler service - make it optional
try:
    from services.web_crawler_service import WebCrawlerService
    WEB_CRAWLER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"WebCrawlerService not available: {e}")
    WebCrawlerService = None
    WEB_CRAWLER_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'md'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize services
embedding_service = EmbeddingService()
chat_service = ChatService()
groq_service = GroqService()  # Fast model for URL classification
rag_service = RAGService(embedding_service)
citation_service = CitationService(embedding_service)
url_selector = URLSelector(groq_service, chat_service)  # Use ChatService for intelligent website selection with better location awareness
document_pipeline = DocumentPipeline(embedding_service, rag_service.pinecone_client)

# Web crawler will be initialized per request (to avoid keeping browser open)
def get_web_crawler():
    """Get a new web crawler instance"""
    if not WEB_CRAWLER_AVAILABLE or WebCrawlerService is None:
        raise ImportError("WebCrawlerService is not available. Crawl4AI may not be properly installed.")
    max_pages = int(os.getenv('CRAWL_MAX_PAGES', '10'))
    timeout = int(os.getenv('CRAWL_TIMEOUT', '30'))
    return WebCrawlerService(max_pages=max_pages, timeout=timeout)

# Conversation memory store (in-memory, keyed by conversation_id)
conversations = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'RAG Backend'}), 200

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Upload and process one or multiple documents.
    Supports parallel processing and immediate vector search.
    """
    try:
        files = request.files.getlist('file')  # Support multiple files
        
        if not files or files[0].filename == '':
            return jsonify({'error': 'No files provided'}), 400
        
        # Get GCS/Google Drive URLs if provided (as form data or JSON)
        drive_urls = []
        if request.form:
            # Get drive_urls from form data (can be multiple, matching files)
            drive_urls_raw = request.form.getlist('gcs_url') or request.form.getlist('drive_url') or request.form.getlist('driveUrl') or request.form.getlist('google_drive_url')
            drive_urls = [url for url in drive_urls_raw if url and url.strip()]
        elif request.is_json:
            # If JSON request, get from JSON body
            data = request.get_json()
            if isinstance(data, dict) and 'gcs_urls' in data:
                drive_urls = data['gcs_urls'] if isinstance(data['gcs_urls'], list) else [data['gcs_urls']]
            elif isinstance(data, dict) and 'gcs_url' in data:
                drive_urls = [data['gcs_url']] if data['gcs_url'] else []
            elif isinstance(data, dict) and 'drive_urls' in data:
                drive_urls = data['drive_urls'] if isinstance(data['drive_urls'], list) else [data['drive_urls']]
            elif isinstance(data, dict) and 'drive_url' in data:
                drive_urls = [data['drive_url']] if data['drive_url'] else []
        
        # Validate and save files
        filepaths = []
        filenames = []
        
        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                filepaths.append(filepath)
                filenames.append(filename)
            else:
                return jsonify({'error': f'File type not allowed: {file.filename}'}), 400
        
        logger.info(f"Processing {len(files)} file(s)...")
        if drive_urls:
            logger.info(f"GCS URLs provided for {len(drive_urls)} file(s): {drive_urls}")
        
        # Process files in parallel with drive URLs
        results = document_pipeline.process_files_parallel(
            filepaths=filepaths,
            filenames=filenames,
            drive_urls=drive_urls if drive_urls else None,  # Pass drive URLs if available
            max_workers=4,  # Adjust based on your server capacity
            split_length=10,
            split_overlap=2,
            batch_size=100
        )
        
        # Clean up uploaded files
        for filepath in filepaths:
            try:
                os.remove(filepath)
            except Exception as e:
                logger.warning(f"Could not delete {filepath}: {e}")
        
        # Summarize results
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        total_chunks = sum(r.get('chunks_count', 0) for r in successful)
        total_vectors = sum(r.get('vectors_uploaded', 0) for r in successful)
        
        return jsonify({
            'message': f'Processed {len(successful)}/{len(results)} file(s) successfully',
            'successful': successful,
            'failed': failed,
            'total_chunks': total_chunks,
            'total_vectors_uploaded': total_vectors,
            'files_processed': len(results)
        }), 200
    
    except Exception as e:
        logger.error(f"Error in upload endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

def decide_chat_mode(query: str, conversation_history: List[Dict[str, str]]) -> str:
    """
    AI Orchestrator: Intelligently decides whether to use RAG (document retrieval) 
    or plain chat based on user intent.
    
    Args:
        query: Current user query
        conversation_history: Recent conversation messages
    
    Returns:
        "rag" for document retrieval, "plain" for conversational chat
    """
    orchestrator_system_prompt = """You are an intelligent routing system for a Dutch government document assistant (WOO - Wet open overheid).

Your task is to analyze the user's query and determine if they need:
1. **RAG (Document Retrieval)** - Retrieve and cite specific information from official documents
2. **PLAIN (Conversational Chat)** - Continue natural conversation, elaborate, clarify, or discuss

**RESPOND WITH ONLY ONE WORD: "rag" OR "plain"**

---

**Use RAG when the user:**
- Asks factual questions requiring specific information from documents
  Examples: "Wat is het registratienummer?", "Welke datum staat in het document?", "Wat zegt de gemeente over...?"
- Requests quotes, citations, or references from documents
  Examples: "Citeer de relevante sectie", "Waar staat dat in het document?"
- Wants to search, find, or look up specific information
  Examples: "Zoek documenten over...", "Geef me informatie over...", "Welke documenten gaan over...?"
- Asks questions starting with: "Wat", "Waar", "Wanneer", "Welk", "Hoeveel" (about document content)
- Needs verification of facts, dates, names, or numbers
  Examples: "Klopt het dat...?", "Is het waar dat...?", "Welke afdeling heeft dit geschreven?"
- Requests summaries or overviews of document content
  Examples: "Vat dit document samen", "Geef me een overzicht van..."
- Wants to compare information across multiple documents
- Asks about legal grounds, policy details, or official statements

**Use PLAIN when the user:**
- Asks for clarification about the previous answer
  Examples: "Kun je dat uitleggen?", "Wat bedoel je daarmee?", "Hoe werkt dat precies?"
- Wants elaboration or more detail about something already discussed
  Examples: "Vertel me meer daarover", "Kun je dat verder toelichten?", "Ga dieper in op..."
- Engages in follow-up questions about the assistant's explanation
  Examples: "Dus als ik het goed begrijp...", "Betekent dit dat...?", "Dus wat je zegt is..."
- Makes casual conversation or expresses opinions/reactions
  Examples: "Interessant!", "Dank je", "Oké, begrepen", "Dat is duidelijk"
- Asks about the assistant's capabilities or how to use the system
  Examples: "Wat kun je voor me doen?", "Hoe werk je?", "Wat voor vragen kan ik stellen?"
- Requests reasoning, explanation, or interpretation (not document quotes)
  Examples: "Waarom is dat zo?", "Wat is het verschil tussen...?", "Hoe zou ik dit interpreteren?"
- Asks hypothetical or scenario-based questions
  Examples: "Wat zou er gebeuren als...?", "Stel dat...", "Hoe zou jij..."
- Continues a topic without needing new document information
- Asks for examples, analogies, or simplified explanations

**Edge cases:**
- If the query contains both elements, prefer RAG (better to over-retrieve than miss information)
- If in doubt and the conversation is just starting, prefer RAG
- If the user explicitly says "zoek", "vind", "geef documenten", always use RAG
- If the user says "leg uit", "vertel", "wat denk je", prefer PLAIN

**Context awareness:**
- Review the last 2-3 conversation turns
- If the user is drilling down on a topic already covered, prefer PLAIN
- If the user introduces a new topic or question, prefer RAG

**Remember:** Your ONLY output should be the word "rag" or "plain" - nothing else."""

    messages = [
        {"role": "system", "content": orchestrator_system_prompt},
    ]
    
    # Add last 4 conversation turns for context (2 exchanges)
    recent_history = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
    messages.extend(recent_history)
    
    # Add the current query with explicit instruction
    messages.append({
        "role": "user", 
        "content": f"Query to analyze: \"{query}\"\n\nShould this use RAG or PLAIN? Respond with only one word."
    })

    try:
        # Use the chat_service to get the mode
        response = chat_service.chat(messages).strip().lower()
        
        # Parse response (handle edge cases)
        if "rag" in response:
            return "rag"
        elif "plain" in response:
            return "plain"
        else:
            # Default to RAG if unclear
            logger.warning(f"Orchestrator returned unclear response: {response}. Defaulting to RAG.")
            return "rag"
    except Exception as e:
        logger.error(f"Error in orchestrator: {e}. Defaulting to RAG.")
        return "rag"


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Unified intelligent chat endpoint with AI orchestration.
    Automatically determines whether to use RAG or plain chat.
    """
    try:
        data = request.get_json()
        query = data.get('query', '')
        conversation_id = data.get('conversation_id', None)
        force_mode = data.get('mode', None)  # Optional: allow manual override

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        # Create or retrieve conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            conversations[conversation_id] = []
        elif conversation_id not in conversations:
            conversations[conversation_id] = []

        logger.info(f"Processing query in conversation {conversation_id}: {query}")

        # Decide mode: use forced mode or orchestrator
        if force_mode in ["rag", "plain"]:
            mode = force_mode
            logger.info(f"Using forced mode: {mode}")
        else:
            mode = decide_chat_mode(query, conversations[conversation_id])
            logger.info(f"🤖 Orchestrator chose mode: {mode}")

        # Execute based on mode
        if mode == "plain":
            # Plain conversational chat
            messages = [
                {
                    "role": "system",
                    "content": "Je bent een behulpzame assistent voor de Nederlandse overheid (WOO - Wet open overheid). Beantwoord vragen op een heldere, professionele en toegankelijke manier. Onthoud eerdere berichten in het gesprek en ga natuurlijk verder met de conversatie. Gebruik GEEN markdown opmaak - schrijf in gewone tekst zonder **bold**, *italic*, lijsten met `-` of `#` headers. Gebruik gewone nummers en normale alinea's."
                }
            ]
            messages.extend(conversations[conversation_id])
            messages.append({
                "role": "user",
                "content": query
            })
            answer = chat_service.chat(messages)
            sources = []
            pdf_citations = []
            
        else:  # mode == "rag"
            # RAG: Retrieve documents and answer with context
            search_results = rag_service.query(
                query=query,
                top_k=5,
                initial_k=30
            )
            
            # Build context from retrieved documents with numbered citations
            context_parts = []
            for i, doc in enumerate(search_results['sources'], 1):
                metadata = doc.get('metadata', {})
                doc_name = metadata.get('document_name', 'Onbekend')
                page_numbers = metadata.get('page_numbers', [])
                page_info = f" (pagina's {', '.join(map(str, page_numbers))})" if page_numbers else ""
                context_parts.append(
                    f"[{i}] Document: {doc_name}{page_info}\n{doc.get('text', '')}"
                )
            context = "\n\n".join(context_parts)
            
            messages = [
                {
                    "role": "system",
                    "content": """Je bent een behulpzame assistent voor de Nederlandse overheid (WOO - Wet open overheid). 

Je taak:
1. Beantwoord de vraag van de gebruiker op basis van de verstrekte documentcontext
2. Citeer specifieke informatie uit de documenten wanneer relevant met [1], [2], etc. format
3. Als de context niet voldoende informatie bevat, zeg dit eerlijk
4. Blijf professioneel en helder in je uitleg
5. Gebruik eerdere berichten in het gesprek om context te behouden

BELANGRIJK: Gebruik GEEN markdown opmaak. Schrijf in gewone tekst zonder:
- **bold** of *italic* opmaak
- Lijsten met `-`, `*`, of genummerde lijsten met `1.`
- Headers met `#`
- Code blocks met backticks

Schrijf gewone alinea's met normale tekst. Gebruik gewone nummers zoals "1.", "2." zonder markdown opmaak. Gebruik citaties [1], [2], etc. om naar documenten te verwijzen. Antwoord altijd in het Nederlands."""
                }
            ]
            
            messages.extend(conversations[conversation_id])
            messages.append({
                "role": "user",
                "content": f"""Context uit documenten:
{context}

Vraag van gebruiker: {query}

Geef een helder antwoord op basis van de bovenstaande context. Gebruik [1], [2], etc. om naar de documenten te verwijzen. Schrijf in gewone tekst zonder markdown opmaak. Gebruik een lege regel tussen genummerde items voor betere leesbaarheid."""
            })
            
            answer = chat_service.chat(messages)
            
            # Format sources as citations (similar to web citations)
            pdf_citations = []
            for i, doc in enumerate(search_results['sources'], 1):
                metadata = doc.get('metadata', {})
                doc_name = metadata.get('document_name', 'Onbekend')
                page_numbers = metadata.get('page_numbers', [])
                page_info = f" (pagina's {', '.join(map(str, page_numbers))})" if page_numbers else ""
                
                # Debug: Log metadata keys and Google Drive URL
                logger.info(f"[Citation] Document: {doc_name}")
                logger.info(f"[Citation] Metadata keys: {list(metadata.keys())}")
                logger.info(f"[Citation] Full metadata: {metadata}")
                
                # Extract GCS/Google Drive link if available in metadata
                drive_url = metadata.get('gcs_url') or metadata.get('gcp_url') or metadata.get('google_drive_url') or metadata.get('drive_url') or metadata.get('gdrive_url') or None
                logger.info(f"[Citation] Extracted drive_url: {drive_url}")
                # Ensure we have a valid URL string (not None or empty)
                if drive_url and isinstance(drive_url, str) and drive_url.strip():
                    citation_url = drive_url.strip()
                    logger.info(f"[Citation] Using Google Drive URL: {citation_url}")
                else:
                    citation_url = f"file://{doc_name}"
                    logger.info(f"[Citation] Using fallback file:// URL: {citation_url}")
                
                # Ensure citation_url is always a valid string (never None)
                if not citation_url or not isinstance(citation_url, str):
                    citation_url = f"file://{doc_name}"
                    logger.warning(f"[Citation] Invalid citation_url, using fallback: {citation_url}")
                
                citation = {
                    'id': str(uuid.uuid4()),
                    'url': str(citation_url),  # Ensure it's a string - Use Google Drive link if available, otherwise file:// protocol
                    'title': doc_name,
                    'snippet': doc.get('text', '')[:300] + ('...' if len(doc.get('text', '')) > 300 else ''),
                    'relevanceScore': doc.get('score', 0.0),
                    'domain': 'Internal Document',
                    'pageNumbers': page_numbers,
                    'documentName': doc_name,
                    'highlightText': doc.get('text', '')[:100],
                    'type': 'document'  # Mark as document citation
                }
                
                logger.info(f"[Citation] Final citation URL: {citation['url']}")
                
                # Add date if available in metadata
                if 'date' in metadata:
                    citation['date'] = metadata['date']
                if 'uploaded_at' in metadata:
                    citation['uploadedAt'] = metadata['uploaded_at']
                    
                pdf_citations.append(citation)
            
            sources = search_results['sources']

        # Store conversation
        conversations[conversation_id].append({
            "role": "user",
            "content": query
        })
        conversations[conversation_id].append({
            "role": "assistant",
            "content": answer
        })

        # Limit history
        if len(conversations[conversation_id]) > 20:
            conversations[conversation_id] = conversations[conversation_id][-20:]

        return jsonify({
            'answer': answer,
            'sources': sources,
            'citations': pdf_citations if mode == 'rag' else [],  # Include PDF citations
            'query': query,
            'conversation_id': conversation_id,
            'message_count': len(conversations[conversation_id]),
            'mode': mode  # Return which mode was used
        }), 200

    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat-plain', methods=['POST'])
def chat_plain():
    """Chat endpoint - plain LLM conversation, no RAG, with memory"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        conversation_id = data.get('conversation_id', None)  # Optional conversation ID

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        # Create or retrieve conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            conversations[conversation_id] = []
        elif conversation_id not in conversations:
            conversations[conversation_id] = []

        logger.info(f"Processing plain chat in conversation {conversation_id}: {query}")

        # Build conversation history for LLM
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Continue the conversation naturally and remember previous messages."
            }
        ]
        messages.extend(conversations[conversation_id])
        
        def generate_stream():
            try:
                has_content = False
                for chunk in chat_service.chat_stream(messages):
                    if chunk:
                        has_content = True
                        # Format as SSE (Server-Sent Events)
                        yield f"data: {json.dumps({'type': 'text', 'text': chunk})}\n\n"
                
                # If no content was received, it might be an error
                if not has_content:
                    error_msg = "Geen antwoord ontvangen van de LLM service. Controleer uw API-sleutels."
                    yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
                else:
                    # Send completion signal
                    yield f"data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error in streaming: {str(e)}")
                # Send user-friendly error message
                error_message = str(e)
                if "401" in error_message or "Unauthorized" in error_message:
                    error_message = "Authenticatiefout: Controleer of uw GROQ_API_KEY correct is ingesteld in de .env file."
                elif "404" in error_message:
                    error_message = "Model niet gevonden. Controleer of het model naam correct is."
                else:
                    error_message = f"Fout bij het genereren van antwoord: {str(e)}"
                
                yield f"data: {json.dumps({'type': 'error', 'error': error_message})}\n\n"
                yield f"data: [DONE]\n\n"

        # Generate answer using ChatService
        logger.info("Generating LLM answer with context...")
        answer = chat_service.chat(messages)

        # Store this exchange in conversation history
        conversations[conversation_id].append({
            "role": "user",
            "content": query
        })
        conversations[conversation_id].append({
            "role": "assistant",
            "content": answer
        })

        # Limit conversation history to last 10 exchanges (20 messages)
        if len(conversations[conversation_id]) > 20:
            conversations[conversation_id] = conversations[conversation_id][-20:]

        return jsonify({
            'answer': answer,
            'query': query,
            'conversation_id': conversation_id,
            'message_count': len(conversations[conversation_id])
        }), 200

    except Exception as e:
        logger.error(f"Error processing plain chat: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    
@app.route('/api/research', methods=['POST'])
def research():
    """Deep research endpoint - Crawl web sources and return answer with citations"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        conversation_id = data.get('conversation_id', None)
        max_results = data.get('max_results', 5)
        # Legacy support: allow URLs to be provided, but prefer websites
        urls = data.get('urls', [])
        websites = data.get('websites', [])  # Optional: specific websites (domains) to crawl
        domain_filter = data.get('domain_filter', [])
        max_pages_per_website = data.get('max_pages_per_website', 10)  # Pages to crawl per website
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Create or retrieve conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            conversations[conversation_id] = []
        elif conversation_id not in conversations:
            conversations[conversation_id] = []
        
        logger.info(f"Starting deep research for query: {query}")
        
        # Initialize web crawler
        web_crawler = get_web_crawler()
        
        try:
            # Select websites using agent (or use provided websites/URLs)
            selected_websites = []
            
            if websites:
                # Use provided websites
                logger.info(f"Using {len(websites)} provided websites")
                # Convert domains to website dicts
                # Access unique_websites through a public method (we'll add one if needed)
                unique_websites = getattr(url_selector, '_unique_websites', [])
                domain_to_website = {w["domain"]: w for w in unique_websites}
                for website_domain in websites:
                    if website_domain in domain_to_website:
                        selected_websites.append(domain_to_website[website_domain])
                    else:
                        # If it's a URL, extract domain and find matching website
                        from urllib.parse import urlparse
                        parsed = urlparse(website_domain if website_domain.startswith('http') else f'https://{website_domain}')
                        domain = parsed.netloc.lower().replace('www.', '')
                        if domain in domain_to_website:
                            selected_websites.append(domain_to_website[domain])
            elif urls:
                # Legacy mode: convert URLs to websites
                logger.info(f"Legacy mode: Converting {len(urls)} URLs to websites for multi-page crawling")
                unique_websites = getattr(url_selector, '_unique_websites', [])
                domain_to_website = {w["domain"]: w for w in unique_websites}
                seen_domains = set()
                for url in urls:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower().replace('www.', '')
                    if domain in domain_to_website and domain not in seen_domains:
                        selected_websites.append(domain_to_website[domain])
                        seen_domains.add(domain)
            else:
                # Agent selects websites automatically
                logger.info(f"No websites/URLs provided, agent selecting relevant websites for query: {query[:100]}...")
                try:
                    # Agent selects websites (default: 2 websites for focused crawling)
                    max_websites = 2
                    selected_websites = url_selector.select_websites(query, max_websites=max_websites)
                except ValueError as e:
                    # Groq-specific errors (API key issues, etc.)
                    error_msg = str(e)
                    logger.error(f"Agent website selection failed: {error_msg}")
                    return jsonify({
                        'error': f'Website selection failed: {error_msg}. Please ensure GROQ_API_KEY is set in your .env file.',
                        'query': query,
                        'conversation_id': conversation_id
                    }), 400
                except Exception as e:
                    logger.error(f"Unexpected error in website selection: {str(e)}", exc_info=True)
                    return jsonify({
                        'error': f'Failed to select websites for crawling: {str(e)}',
                        'query': query,
                        'conversation_id': conversation_id
                    }), 500
            
            if not selected_websites:
                return jsonify({
                    'error': 'Could not find relevant government websites for your query. Please try rephrasing your question.',
                    'query': query,
                    'conversation_id': conversation_id
                }), 200
            
            logger.info(f"Agent selected {len(selected_websites)} websites for multi-page crawling")
            for i, website in enumerate(selected_websites, 1):
                logger.info(f"  [{i}] {website['domain']} (entry: {website['entry_url']})")
            
            # Filter by allowed domains if domain_filter provided
            if domain_filter:
                web_crawler.allowed_domains = domain_filter
            
            # Crawl each website for multiple pages
            # Use a single event loop for both crawling and cleanup to avoid loop conflicts
            logger.info(f"Starting multi-page crawl of {len(selected_websites)} websites for query: '{query[:100]}'...")
            
            # Create event loop for this request
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            crawled_content = []
            
            async def crawl_all_websites():
                """Async function to crawl all selected websites in parallel"""
                try:
                    # Crawl all websites in parallel for faster execution
                    logger.info(f"Starting parallel crawl of {len(selected_websites)} websites")
                    
                    async def crawl_single_website(website: Dict, index: int) -> List[Dict]:
                        """Crawl a single website"""
                        domain = website['domain']
                        entry_url = website['entry_url']
                        title = website.get('title', domain)
                        
                        logger.info(f"[Website {index+1}/{len(selected_websites)}] Starting multi-page crawl: {domain}")
                        
                        try:
                            # Use multi-page crawling for this website
                            website_content = await web_crawler.crawl_website_multi_page(
                                entry_url=entry_url,
                                query=query,
                                max_pages=max_pages_per_website,
                                depth=2  # Crawl entry page + linked pages
                            )
                            
                            if website_content:
                                logger.info(f"[Website {index+1}/{len(selected_websites)}] ✓ Crawled {len(website_content)} pages from {domain}")
                                return website_content
                            else:
                                logger.warning(f"[Website {index+1}/{len(selected_websites)}] ✗ No content crawled from {domain}")
                                return []
                        except Exception as e:
                            logger.error(f"[Website {index+1}/{len(selected_websites)}] ✗ Error crawling {domain}: {str(e)}")
                            return []
                    
                    # Create tasks for all websites
                    tasks = [crawl_single_website(website, i) for i, website in enumerate(selected_websites)]
                    
                    # Execute all website crawls in parallel
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Collect all results
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"Exception during crawl of website {selected_websites[i]['domain']}: {str(result)}")
                        elif isinstance(result, list):
                            crawled_content.extend(result)
                    
                    logger.info(f"Completed parallel crawl: {len(crawled_content)} total pages from {len(selected_websites)} websites")
                    
                finally:
                    # Always clean up, even if crawling failed
                    try:
                        await web_crawler.close()
                    except Exception as e:
                        # Cleanup errors are non-critical - browser processes will be cleaned up by OS
                        logger.debug(f"Non-critical cleanup error (browser will auto-cleanup): {str(e)}")
            
            try:
                loop.run_until_complete(crawl_all_websites())
            finally:
                loop.close()
                # Clear the event loop from thread-local storage
                asyncio.set_event_loop(None)
            
            if not crawled_content:
                logger.warning(f"No crawled content retrieved from {len(selected_websites)} websites")
                return jsonify({
                    'error': 'No content could be retrieved from the selected websites. The websites may be unreachable or blocking crawlers.',
                    'query': query,
                    'conversation_id': conversation_id,
                    'websites_attempted': [w['domain'] for w in selected_websites],
                    'crawled_websites': []
                }), 200
            
            # Extract unique crawled pages with titles for display
            crawled_websites = []
            seen_urls = set()
            domain_to_info = {}  # Track domain info
            for content in crawled_content:
                url = content.get('url', '')
                domain = content.get('domain', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    crawled_websites.append({
                        'url': url,
                        'title': content.get('title', ''),
                        'domain': domain
                    })
                    # Track domain info
                    if domain not in domain_to_info:
                        domain_to_info[domain] = {
                            'domain': domain,
                            'pages_crawled': 0,
                            'entry_url': url  # First URL seen for this domain
                        }
                    domain_to_info[domain]['pages_crawled'] += 1
            
            # Create summary of crawled websites (domains) with page counts
            website_summary = []
            for domain, info in domain_to_info.items():
                website_summary.append({
                    'domain': domain,
                    'entry_url': info['entry_url'],
                    'pages_crawled': info['pages_crawled']
                })
            
            # Process citations: score, format, deduplicate
            logger.info(f"Processing {len(crawled_content)} citations...")
            citations = citation_service.process_citations(
                query=query,
                crawled_content=crawled_content,
                top_k=max_results
            )
            
            # Build context from citations
            context_parts = []
            for i, citation in enumerate(citations, 1):
                context_parts.append(
                    f"[{i}] Source: {citation['title']} ({citation['url']})\n"
                    f"Snippet: {citation['snippet']}\n"
                )
            context = "\n\n".join(context_parts)
            
            # Build conversation history for LLM
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides answers based on web sources. Always cite your sources using [1], [2], etc. format when referencing information from the provided context. If the context doesn't contain relevant information, say so. IMPORTANT: Do NOT use markdown formatting. Write in plain text without **bold**, *italic*, lists with `-` or `#` headers. Use regular paragraphs and normal text formatting."
                }
            ]
            
            # Add conversation history
            messages.extend(conversations[conversation_id])
            
            # Build website summary for context
            website_list = []
            for i, site in enumerate(website_summary, 1):
                website_list.append(f"[Website {i}] {site['domain']} ({site['pages_crawled']} pages crawled)")
            websites_context = "\n".join(website_list) if website_list else ""
            
            # Add current query with context
            user_content = f"Web Sources Context:\n{context}\n\n"
            if websites_context:
                user_content += f"Websites crawled:\n{websites_context}\n\n"
            user_content += f"User question: {query}\n\nProvide an answer based on the sources above, citing them with [1], [2], etc. Also mention which websites were crawled at the end of your answer. Write in plain text without markdown formatting - no **bold**, no *italic*, no lists with `-` or `#` headers. Use regular paragraphs and normal text."
            
            messages.append({
                "role": "user",
                "content": user_content
            })
            
            # Generate answer using ChatService
            logger.info("Generating LLM answer...")
            answer = chat_service.chat(messages)
            
            # Store this exchange in conversation history
            conversations[conversation_id].append({
                "role": "user",
                "content": query
            })
            conversations[conversation_id].append({
                "role": "assistant",
                "content": answer
            })
            
            # Limit conversation history
            if len(conversations[conversation_id]) > 20:
                conversations[conversation_id] = conversations[conversation_id][-20:]
            
            # Prepare selected websites info for frontend display
            selected_websites_info = [
                {
                    'domain': w['domain'],
                    'title': w.get('title', w['domain']),
                    'entry_url': w['entry_url']
                }
                for w in selected_websites
            ]
            
            # Return response with citations and crawled websites
            response_data = {
                'answer': answer,
                'citations': citations,
                'crawled_websites': crawled_websites,  # List of pages that were crawled
                'website_summary': website_summary,  # Summary of websites with page counts
                'selected_websites': selected_websites_info,  # Info about websites selected for crawling
                'query': query,
                'conversation_id': conversation_id,
                'message_count': len(conversations[conversation_id]),
                'citations_count': len(citations),
                'total_pages_crawled': len(crawled_websites)
            }
            logger.info(f"Research response: answer_length={len(answer)}, citations={len(citations)}, websites={len(crawled_websites)}")
            return jsonify(response_data), 200
        
        except Exception as e:
            logger.error(f"Error in research: {str(e)}", exc_info=True)
            return jsonify({'error': f'Research error: {str(e)}'}), 500
    
    except Exception as e:
        logger.error(f"Error processing research request: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents', methods=['GET'])
def list_documents():
    """List all indexed documents"""
    try:
        docs = rag_service.list_documents()
        return jsonify({'documents': docs}), 200
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Delete a document by ID"""
    try:
        rag_service.delete_document(doc_id)
        return jsonify({'message': 'Document deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get conversation history"""
    try:
        if conversation_id not in conversations:
            return jsonify({'error': 'Conversation not found'}), 404
        
        return jsonify({
            'conversation_id': conversation_id,
            'messages': conversations[conversation_id]
        }), 200
    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def clear_conversation(conversation_id):
    """Clear conversation history"""
    try:
        if conversation_id in conversations:
            del conversations[conversation_id]
        
        return jsonify({'message': 'Conversation cleared'}), 200
    except Exception as e:
        logger.error(f"Error clearing conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    """List all active conversations"""
    try:
        return jsonify({
            'conversations': [
                {
                    'id': conv_id,
                    'message_count': len(messages)
                }
                for conv_id, messages in conversations.items()
            ]
        }), 200
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
