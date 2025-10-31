const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5001';

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();

    // Get the last user message
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage || lastMessage.role !== 'user') {
      return new Response('Invalid request', { status: 400 });
    }

    // Extract text from message
    const userQuery = lastMessage.content || '';

    // Call backend RAG service which handles both retrieval and generation
    try {
      const ragResponse = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: userQuery }),
      });

      if (!ragResponse.ok) {
        const errorData = await ragResponse.json().catch(() => ({ error: ragResponse.statusText }));
        throw new Error(`Backend error: ${ragResponse.status} - ${errorData.error || ragResponse.statusText}`);
      }

      const ragData = await ragResponse.json();
      
      // Create a streaming response that sends the answer
      const encoder = new TextEncoder();
      const stream = new ReadableStream({
        start(controller) {
          // Send the answer as a streaming response
          const answer = ragData.answer || 'Ik kon geen antwoord vinden op uw vraag.';
          
          // Split the answer into chunks for streaming effect
          const words = answer.split(' ');
          let currentChunk = '';
          
          const sendChunk = (index: number) => {
            if (index >= words.length) {
              // Send final chunk and close
              controller.enqueue(encoder.encode(`data: {"type":"text","text":""}

`));
              controller.enqueue(encoder.encode(`data: [DONE]

`));
              controller.close();
              return;
            }
            
            currentChunk += (index > 0 ? ' ' : '') + words[index];
            
            // Send chunk every few words
            if (index % 3 === 0 || index === words.length - 1) {
              const chunk = {
                type: 'text',
                text: currentChunk
              };
              controller.enqueue(encoder.encode(`data: ${JSON.stringify(chunk)}\n\n`));
              currentChunk = '';
            }
            
            // Continue with next word after a small delay
            setTimeout(() => sendChunk(index + 1), 50);
          };
          
          // Start sending chunks
          sendChunk(0);
        }
      });

      return new Response(stream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
      
    } catch (ragError) {
      console.error('RAG service error:', ragError);
      throw ragError;
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
