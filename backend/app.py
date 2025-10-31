from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
from werkzeug.utils import secure_filename
import os
import asyncio
from services.document_processor import DocumentProcessor
from services.rag_service import RAGService
from services.llm_service import EmbeddingService, ChatService
try:
    from services.web_crawler_service import WebCrawlerService
    WEB_CRAWLER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"WebCrawlerService not available: {e}")
    WebCrawlerService = None
    WEB_CRAWLER_AVAILABLE = False

from services.citation_service import CitationService
import logging
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
doc_processor = DocumentProcessor()
rag_service = RAGService(embedding_service)
citation_service = CitationService(embedding_service)

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
    """Upload and process document"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            logger.info(f"Processing file: {filename}")
            
            # Extract text from document
            text = doc_processor.extract_text(filepath)
            
            # Chunk the document
            chunks = doc_processor.chunk_text(text)
            
            # Generate embeddings and store in Qdrant
            doc_id = rag_service.index_document(
                chunks=chunks,
                metadata={
                    'filename': filename,
                    'source': filename,
                    'upload_date': doc_processor.get_current_timestamp()
                }
            )
            
            # Clean up uploaded file
            os.remove(filepath)
            
            return jsonify({
                'message': 'File processed successfully',
                'document_id': doc_id,
                'chunks_count': len(chunks),
                'filename': filename
            }), 200
        
        return jsonify({'error': 'File type not allowed'}), 400
    
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint - RAG query with LLM response and conversation memory"""
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
        
        logger.info(f"Processing query in conversation {conversation_id}: {query}")
        
        # Get relevant documents from vector search with reranking
        # Retrieve 30 documents from Pinecone, then rerank to top 5
        search_results = rag_service.query(
            query=query, 
            top_k=5,        # Final number of documents after reranking
            initial_k=30    # Initial retrieval from Pinecone
        )
        
        # Build context from retrieved documents
        context = "\n\n".join([doc.get('text', '') for doc in search_results['sources']])
        
        # Build conversation history for LLM
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer the user's question based on the provided context and conversation history. If the context doesn't contain relevant information, say so. Maintain context from previous messages in the conversation."
            }
        ]
        
        # Add conversation history
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
        # Add current query with context
        messages.append({
            "role": "user",
            "content": f"Context from documents:\n{context}\n\nUser question: {query}"
        })
        
        # Generate answer using ChatService
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
            'sources': search_results['sources'],
            'query': query,
            'conversation_id': conversation_id,
            'message_count': len(conversations[conversation_id])
        }), 200
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
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
                # For now, we'll require URLs to be provided
                # In future, could integrate with search APIs
                return jsonify({
                    'error': 'URLs required for research. Please provide URLs to crawl.'
                }), 400
            
            # Filter URLs by allowed domains if domain_filter provided
            if domain_filter:
                web_crawler.allowed_domains = domain_filter
            
            # Crawl URLs
            logger.info(f"Crawling {len(urls)} URLs...")
            crawled_content = asyncio.run(
                web_crawler.crawl_urls(urls, query)
            )
            
            if not crawled_content:
                return jsonify({
                    'error': 'No content could be retrieved from the provided URLs.',
                    'query': query,
                    'conversation_id': conversation_id
                }), 200
            
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
            
            # Add current query with context
            messages.append({
                "role": "user",
                "content": f"Web Sources Context:\n{context}\n\nUser question: {query}\n\nProvide an answer based on the sources above, citing them with [1], [2], etc."
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
            
            # Return response with citations
            return jsonify({
                'answer': answer,
                'citations': citations,
                'query': query,
                'conversation_id': conversation_id,
                'message_count': len(conversations[conversation_id]),
                'citations_count': len(citations)
            }), 200
        
        except Exception as e:
            logger.error(f"Error in research: {str(e)}")
            return jsonify({'error': f'Research error: {str(e)}'}), 500
        finally:
            # Clean up crawler
            try:
                asyncio.run(web_crawler.close())
            except Exception as e:
                logger.warning(f"Error closing crawler: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error processing research request: {str(e)}")
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
