from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
from werkzeug.utils import secure_filename
import os
import asyncio
import requests
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
                
                # Get the text for highlighting - it's in metadata, not doc!
                full_text = metadata.get('text', '') or doc.get('text', '')
                logger.info(f"[Citation] DOC KEYS: {list(doc.keys())}")
                logger.info(f"[Citation] Full text length: {len(full_text)}")
                logger.info(f"[Citation] Full text sample: {full_text[:200] if full_text else 'EMPTY'}")
                
                citation = {
                    'id': str(uuid.uuid4()),
                    'url': str(citation_url),  # Ensure it's a string - Use Google Drive link if available, otherwise file:// protocol
                    'title': doc_name,
                    'snippet': full_text[:300] + ('...' if len(full_text) > 300 else ''),
                    'relevanceScore': doc.get('score', 0.0),
                    'domain': 'Internal Document',
                    'pageNumbers': page_numbers,
                    'documentName': doc_name,
                    'highlightText': full_text,  # Full text for highlighting in PDF viewer
                    'type': 'document'  # Mark as document citation
                }
                
                logger.info(f"[Citation] Citation highlightText length: {len(citation['highlightText'])}")
                
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
    """Government data research endpoint - Search Dutch government APIs and return answer with citations"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        conversation_id = data.get('conversation_id', None)
        max_results = data.get('max_results', 10)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Create or retrieve conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            conversations[conversation_id] = []
        elif conversation_id not in conversations:
            conversations[conversation_id] = []
        
        logger.info(f"Starting government data research for query: {query}")
        
        # Import new services
        from services.government_data_service import GovernmentDataService
        from services.api_endpoint_selector import APIEndpointSelector
        
        # Initialize services
        gov_data_service = GovernmentDataService()
        api_selector = APIEndpointSelector(groq_service)
        
        try:
            # Step 1: AI agent selects API parameters based on query
            logger.info("Using AI agent to select API parameters...")
            api_params = api_selector.select_api_parameters(query)
            logger.info(f"AI agent selected parameters: {api_params}")
            
            # Step 2: Call government data API with selected parameters
            logger.info(f"Searching data.overheid.nl API...")
            clean_context, citations, metadata = gov_data_service.search_and_parse(
                query=api_params['search_query'],
                rows=api_params['rows'],
                filters=api_params.get('filters'),
                sort=api_params.get('sort')
            )
            
            # Check if search was successful
            if not metadata.get('success'):
                error_msg = metadata.get('error', 'Unknown error')
                logger.error(f"API search failed: {error_msg}")
                return jsonify({
                    'error': f'Failed to search government data: {error_msg}',
                    'query': query,
                    'conversation_id': conversation_id
                }), 500
            
            if not citations:
                logger.warning(f"No results found for query: {query}")
                return jsonify({
                    'error': 'Geen resultaten gevonden. Probeer uw zoekopdracht te herformuleren.',
                    'query': query,
                    'conversation_id': conversation_id,
                    'total_count': metadata.get('total_count', 0)
                }), 200
            
            logger.info(f"Found {metadata.get('total_count', 0)} total results, using {len(citations)} citations")
            
            # Step 3: Build LLM prompt with CLEAN CONTEXT ONLY (no metadata!)
            # This is critical - LLM receives only readable text, no JSON, no API structure
            messages = [
                {
                    "role": "system",
                    "content": """Je bent een expert assistent die vragen beantwoordt op basis van Nederlandse overheidsinformatie.

Je taak:
1. Beantwoord de vraag van de gebruiker op basis van de verstrekte bronnen
2. Citeer specifieke informatie met [1], [2], etc. formaat
3. Als de bronnen niet voldoende informatie bevatten, zeg dit eerlijk
4. Blijf professioneel en helder in je uitleg
5. Gebruik eerdere berichten in het gesprek om context te behouden

BELANGRIJK: Gebruik GEEN markdown opmaak. Schrijf in gewone tekst zonder:
- **bold** of *italic* opmaak
- Lijsten met `-`, `*`, of genummerde lijsten met markdown
- Headers met `#`
- Code blocks met backticks

Schrijf gewone alinea's met normale tekst. Gebruik citaties [1], [2], etc. om naar bronnen te verwijzen."""
                }
            ]
            
            # Add conversation history
            messages.extend(conversations[conversation_id])
            
            # Add current query with CLEAN context (no metadata!)
            user_content = f"""Bronnen uit data.overheid.nl:

{clean_context}

Vraag van gebruiker: {query}

Geef een helder antwoord op basis van de bovenstaande bronnen. Gebruik [1], [2], etc. om naar de bronnen te verwijzen. Schrijf in gewone tekst zonder markdown opmaak."""
            
            messages.append({
                "role": "user",
                "content": user_content
            })
            
            # Step 4: Generate answer using ChatService
            logger.info("Generating LLM answer with clean context...")
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
            
            # Step 5: Return response with answer and FULL citations (with metadata)
            response_data = {
                'answer': answer,
                'citations': citations,  # Full citation objects with all metadata
                'query': query,
                'conversation_id': conversation_id,
                'message_count': len(conversations[conversation_id]),
                'citations_count': len(citations),
                'total_count': metadata.get('total_count', 0),
                'source': 'data.overheid.nl',
                'search_query': api_params['search_query']
            }
            
            logger.info(f"Research response: answer_length={len(answer)}, citations={len(citations)}, total_available={metadata.get('total_count', 0)}")
            return jsonify(response_data), 200
        
        except Exception as e:
            logger.error(f"Error in research: {str(e)}", exc_info=True)
            return jsonify({'error': f'Research error: {str(e)}'}), 500
    
    except Exception as e:
        logger.error(f"Error processing research request: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy-document', methods=['GET'])
def proxy_document():
    """
    Proxy government documents to avoid CORS issues
    Fetches PDFs/documents from data.overheid.nl and serves them to frontend
    """
    try:
        document_url = request.args.get('url')
        
        if not document_url:
            return jsonify({'error': 'URL parameter is required'}), 400
        
        # Validate URL is from trusted government sources
        trusted_domains = [
            'data.overheid.nl',
            'open-overheid.nl',
            'officielebekendmakingen.nl',
            'rijksoverheid.nl',
            'cbs.nl'
        ]
        
        from urllib.parse import urlparse
        parsed_url = urlparse(document_url)
        is_trusted = any(domain in parsed_url.netloc for domain in trusted_domains)
        
        if not is_trusted:
            logger.warning(f"Attempted to proxy non-trusted URL: {document_url}")
            return jsonify({'error': 'URL not from trusted government source'}), 403
        
        logger.info(f"Proxying document from: {document_url}")
        
        # Fetch the document
        response = requests.get(document_url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Get content type
        content_type = response.headers.get('Content-Type', 'application/pdf')
        
        # Stream the response back to client
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        return Response(
            generate(),
            content_type=content_type,
            headers={
                'Content-Disposition': response.headers.get('Content-Disposition', 'inline'),
                'Access-Control-Allow-Origin': '*'
            }
        )
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching document: {document_url}")
        return jsonify({'error': 'Document request timeout'}), 504
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching document: {str(e)}")
        return jsonify({'error': f'Failed to fetch document: {str(e)}'}), 502
    except Exception as e:
        logger.error(f"Error proxying document: {str(e)}")
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
