const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5001';

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();

    // Validate messages
    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return new Response('Invalid request: messages required', { status: 400 });
    }

    // Send messages directly to backend for RAG processing and streaming
    const backendResponse = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ messages }),
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({ error: backendResponse.statusText }));
      throw new Error(`Backend error: ${backendResponse.status} - ${errorData.error || backendResponse.statusText}`);
    }

    // Check if response is streaming
    const contentType = backendResponse.headers.get('content-type');
    if (contentType && contentType.includes('text/event-stream')) {
      // Return the streaming response directly from backend
      return new Response(backendResponse.body, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    } else {
      // Handle non-streaming response (fallback)
      const data = await backendResponse.json();
      const encoder = new TextEncoder();
      
      const stream = new ReadableStream({
        start(controller) {
          const answer = data.answer || 'Ik kon geen antwoord vinden op uw vraag.';
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'text', text: answer })}\n\n`));
          controller.enqueue(encoder.encode(`data: [DONE]\n\n`));
          controller.close();
        }
      });

      return new Response(stream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    }
    
  } catch (error: any) {
    console.error('Chat API error:', error);
    const errorMessage = error instanceof Error ? error.message : 'Internal server error';

    return new Response(
      JSON.stringify({
        error: errorMessage,
        type: 'error'
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
