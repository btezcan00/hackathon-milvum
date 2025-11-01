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
url_selector = URLSelector(groq_service)  # Use Groq for fast URL selection
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
        
        # Validate and save files
        filepaths = []
        filenames = []
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                filepaths.append(filepath)
                filenames.append(filename)
            else:
                return jsonify({'error': f'File type not allowed: {file.filename}'}), 400
        
        logger.info(f"Processing {len(files)} file(s)...")
        
        # Process files in parallel
        results = document_pipeline.process_files_parallel(
            filepaths=filepaths,
            filenames=filenames,
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
                    "content": "Je bent een behulpzame assistent voor de Nederlandse overheid (WOO - Wet open overheid). Beantwoord vragen op een heldere, professionele en toegankelijke manier. Onthoud eerdere berichten in het gesprek en ga natuurlijk verder met de conversatie."
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

Antwoord altijd in het Nederlands. Gebruik citaties [1], [2], etc. om naar documenten te verwijzen."""
                }
            ]
            
            messages.extend(conversations[conversation_id])
            messages.append({
                "role": "user",
                "content": f"""Context uit documenten:
{context}

Vraag van gebruiker: {query}

Geef een helder antwoord op basis van de bovenstaande context. Gebruik [1], [2], etc. om naar de documenten te verwijzen."""
            })
            
            answer = chat_service.chat(messages)
            
            # Format sources as citations (similar to web citations)
            pdf_citations = []
            for i, doc in enumerate(search_results['sources'], 1):
                metadata = doc.get('metadata', {})
                doc_name = metadata.get('document_name', 'Onbekend')
                page_numbers = metadata.get('page_numbers', [])
                page_info = f" (pagina's {', '.join(map(str, page_numbers))})" if page_numbers else ""
                
                # Extract Google Drive link if available in metadata
                drive_url = metadata.get('google_drive_url') or metadata.get('drive_url') or metadata.get('gdrive_url') or ''
                
                citation = {
                    'id': str(uuid.uuid4()),
                    'url': drive_url or f"file://{doc_name}",  # Use Google Drive link if available, otherwise file:// protocol
                    'title': doc_name,
                    'snippet': doc.get('text', '')[:300] + ('...' if len(doc.get('text', '')) > 300 else ''),
                    'relevanceScore': doc.get('score', 0.0),
                    'domain': 'Internal Document',
                    'pageNumbers': page_numbers,
                    'documentName': doc_name,
                    'highlightText': doc.get('text', '')[:100],
                    'type': 'document'  # Mark as document citation
                }
                
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
        urls = data.get('urls', [])  # Optional: specific URLs to crawl
        domain_filter = data.get('domain_filter', [])
        
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
            # Generate or use provided URLs
            if not urls:
                # Automatically select relevant URLs based on the query using Groq
                logger.info(f"No URLs provided, selecting relevant URLs using Groq for query: {query[:100]}...")
                try:
                    urls = url_selector.select_urls(query, max_urls=max_results + 2)  # Get a few extra URLs for safety
                except ValueError as e:
                    # Groq-specific errors (API key issues, etc.)
                    error_msg = str(e)
                    logger.error(f"Groq URL selection failed: {error_msg}")
                    return jsonify({
                        'error': f'URL selection failed: {error_msg}. Please ensure GROQ_API_KEY is set in your .env file.',
                        'query': query,
                        'conversation_id': conversation_id
                    }), 400
                except Exception as e:
                    logger.error(f"Unexpected error in URL selection: {str(e)}", exc_info=True)
                    return jsonify({
                        'error': f'Failed to select URLs for crawling: {str(e)}',
                        'query': query,
                        'conversation_id': conversation_id
                    }), 500
                
                if not urls:
                    return jsonify({
                        'error': 'Could not find relevant government sources for your query. Please try rephrasing your question.',
                        'query': query,
                        'conversation_id': conversation_id
                    }), 200
                
                logger.info(f"Selected {len(urls)} URLs automatically")
                for i, url in enumerate(urls, 1):
                    logger.info(f"  [{i}] {url}")
            
            # Filter URLs by allowed domains if domain_filter provided
            if domain_filter:
                web_crawler.allowed_domains = domain_filter
            
            # Crawl URLs
            # Use a single event loop for both crawling and cleanup to avoid loop conflicts
            logger.info(f"Starting to crawl {len(urls)} URLs for query: '{query[:100]}'...")
            for i, url in enumerate(urls, 1):
                logger.info(f"  Will crawl [{i}/{len(urls)}]: {url}")
            
            # Create event loop for this request
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            crawled_content = []
            try:
                crawled_content = loop.run_until_complete(
                    web_crawler.crawl_urls(urls, query)
                )
            finally:
                # Always clean up in the same loop, even if crawling failed
                try:
                    loop.run_until_complete(web_crawler.close())
                except Exception as e:
                    # Cleanup errors are non-critical - browser processes will be cleaned up by OS
                    logger.debug(f"Non-critical cleanup error (browser will auto-cleanup): {str(e)}")
                finally:
                    loop.close()
                    # Clear the event loop from thread-local storage
                    asyncio.set_event_loop(None)
            
            if not crawled_content:
                logger.warning(f"No crawled content retrieved from {len(urls)} URLs")
                return jsonify({
                    'error': 'No content could be retrieved from the provided URLs. The websites may be unreachable or blocking crawlers.',
                    'query': query,
                    'conversation_id': conversation_id,
                    'urls_attempted': urls,
                    'crawled_websites': crawled_websites if 'crawled_websites' in locals() else []
                }), 200
            
            # Extract unique crawled URLs with titles for display
            crawled_websites = []
            seen_urls = set()
            for content in crawled_content:
                url = content.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    crawled_websites.append({
                        'url': url,
                        'title': content.get('title', ''),
                        'domain': content.get('domain', '')
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
                    "content": "You are a helpful assistant that provides answers based on web sources. Always cite your sources using [1], [2], etc. format when referencing information from the provided context. If the context doesn't contain relevant information, say so."
                }
            ]
            
            # Add conversation history
            messages.extend(conversations[conversation_id])
            
            # Build website list for context
            website_list = []
            for i, site in enumerate(crawled_websites, 1):
                website_list.append(f"[Website {i}] {site['title']} - {site['url']}")
            websites_context = "\n".join(website_list) if website_list else ""
            
            # Add current query with context
            user_content = f"Web Sources Context:\n{context}\n\n"
            if websites_context:
                user_content += f"Websites crawled:\n{websites_context}\n\n"
            user_content += f"User question: {query}\n\nProvide an answer based on the sources above, citing them with [1], [2], etc. Also mention which websites were crawled at the end of your answer."
            
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
            
            # Return response with citations and crawled websites
            response_data = {
                'answer': answer,
                'citations': citations,
                'crawled_websites': crawled_websites,  # List of URLs that were crawled
                'query': query,
                'conversation_id': conversation_id,
                'message_count': len(conversations[conversation_id]),
                'citations_count': len(citations)
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
