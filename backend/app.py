from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from services.document_processor import DocumentProcessor
from services.rag_service import RAGService
from services.embedding_service import EmbeddingService
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
doc_processor = DocumentProcessor()
qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
rag_service = RAGService(embedding_service, qdrant_host=qdrant_host, qdrant_port=qdrant_port)

# Initialize Qdrant collection on app startup
# Note: Embedding model loads lazily on first use
try:
    rag_service.initialize()
    logger.info("RAG service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize RAG service: {str(e)}")
    logger.info("App will continue but RAG features may not work until services are ready")

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
    """Chat endpoint - RAG query"""
    try:
        data = request.get_json()
        logger.info(f"Received data: {data}")
        query = data.get('query', '') if data else ''

        if not query:
            logger.warning(f"Empty query received. Data: {data}")
            return jsonify({'error': 'Query is required'}), 400
        
        logger.info(f"Processing query: {query}")
        
        # Get RAG response
        response = rag_service.query(
            query=query,
            top_k=5
        )
        
        return jsonify({
            'answer': response['answer'],
            'sources': response['sources'],
            'query': query
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
