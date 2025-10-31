const GROQ_API_KEY = process.env.GROQ_API_KEY || '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';
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

    // Get RAG context from backend
    let ragContext = '';
    let ragSources: any[] = [];

    try {
      const ragResponse = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: userQuery }),
      });

      if (ragResponse.ok) {
        const ragData = await ragResponse.json();
        ragSources = ragData.sources || [];

        // Combine context from sources
        const contextTexts = ragSources
          .slice(0, 3) // Use top 3 sources
          .map((source: any) => source.text)
          .filter(Boolean);

        if (contextTexts.length > 0) {
          ragContext = `Relevante informatie uit geüploade documenten:\n\n${contextTexts.join('\n\n')}`;
        }
      }
    } catch (ragError) {
      console.warn('RAG context fetch failed, continuing without context:', ragError);
    }

    // Build messages for LLM
    const systemMessage = ragContext
      ? `Je bent een behulpzame assistent. Gebruik de volgende context uit geüploade documenten om vragen te beantwoorden. Als de context geen relevante informatie bevat, geef dan aan dat je de informatie niet in de documenten hebt gevonden.\n\n${ragContext}`
      : 'Je bent een behulpzame assistent. Beantwoord vragen op basis van de beschikbare informatie.';

    // Convert messages format for Groq API
    const formattedMessages: Array<{ role: 'user' | 'assistant' | 'system'; content: string }> = [
      {
        role: 'system',
        content: systemMessage,
      }
    ];

    // Add conversation history
    for (const msg of messages) {
      formattedMessages.push({
        role: msg.role as 'user' | 'assistant',
        content: msg.content || '',
      });
    }

    // Call Groq API directly
    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${GROQ_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'llama-3.3-70b-versatile',
        messages: formattedMessages,
        temperature: 0.6,
        max_tokens: 4096,
        top_p: 0.95,
        stream: true,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Groq API error: ${response.status} - ${errorText}`);
    }

    // Return the stream directly (SSE format)
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
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
