from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
from werkzeug.utils import secure_filename
import os
from services.document_processor import DocumentProcessor
from services.rag_service import RAGService
from services.llm_service import EmbeddingService, ChatService
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
        
        # Get relevant documents from vector search
        search_results = rag_service.query(query=query, top_k=5)
        
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
                for chunk in chat_service.chat_stream(llm_messages):
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
