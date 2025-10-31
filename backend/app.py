from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
from werkzeug.utils import secure_filename
import os
from services.document_processor import DocumentProcessor
from services.rag_service import RAGService
from services.llm_service import EmbeddingService, ChatService
import logging

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
    """Streaming chat endpoint - RAG query with LLM response"""
    try:
        data = request.get_json()
        logger.info(f"Received data: {data}")
        
        # Handle both 'query' and 'messages' formats
        if 'messages' in data:
            # Extract last user message
            messages = data['messages']
            last_message = messages[-1] if messages else {}
            query = last_message.get('content', '') if last_message.get('role') == 'user' else ''
        else:
            query = data.get('query', '') if data else ''

        if not query:
            logger.warning(f"Empty query received. Data: {data}")
            return jsonify({'error': 'Query is required'}), 400
        
        logger.info(f"Processing query: {query}")
        
        # Get relevant documents from vector search
        search_results = rag_service.query(query=query, top_k=5)
        logger.info(f"Found {len(search_results['sources'])} relevant sources")
        
        # Build context from retrieved documents
        context = "\n\n".join([doc.get('text', '') for doc in search_results['sources']])
        
        # Prepare system message with context
        system_content = "Je bent een behulpzame assistent voor de Nederlandse overheid. Beantwoord vragen op basis van de verstrekte context uit officiële documenten. Als de context geen relevante informatie bevat, geef dit duidelijk aan. Antwoord altijd in het Nederlands."
        
        if context.strip():
            system_content += f"\n\nContext uit geüploade documenten:\n{context}"
        
        # Generate streaming response using ChatService
        llm_messages = [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": query
            }
        ]
        
        logger.info(f"Messages for LLM: {llm_messages}")
        
        def generate_stream():
            try:
                for chunk in chat_service.chat_stream(llm_messages):
                    if chunk:
                        # Format as SSE (Server-Sent Events)
                        yield f"data: {json.dumps({'type': 'text', 'text': chunk})}\n\n"
                
                # Send completion signal
                yield f"data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error in streaming: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        return Response(
            generate_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
