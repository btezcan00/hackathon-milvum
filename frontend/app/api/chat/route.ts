const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5001';

export async function POST(req: Request) {
  try {
    const body = await req.json();

    // Backend expects { query } format, but frontend may send { messages }
    // Extract query from messages if needed
    let query = body.query;
    const conversation_id = body.conversation_id;

    if (body.messages && Array.isArray(body.messages) && body.messages.length > 0) {
      // Find the last user message
      const lastUserMessage = body.messages.slice().reverse().find((msg: { role: string; content: string }) => msg.role === 'user');
      if (lastUserMessage) {
        query = lastUserMessage.content;
      }
    }

    // Validate query
    if (!query) {
      return new Response('Invalid request: query is required', { status: 400 });
    }

    // Send to backend in the format it expects
    const backendResponse = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query,
        conversation_id: conversation_id
      }),
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
      // Handle non-streaming JSON response
      const data = await backendResponse.json();
      
      // If it's a JSON response with answer and citations, return as JSON (not stream)
      if (data.answer && typeof data.answer === 'string') {
        return new Response(JSON.stringify(data), {
          headers: {
            'Content-Type': 'application/json',
          },
        });
      }
      
      // Fallback: convert to stream
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
