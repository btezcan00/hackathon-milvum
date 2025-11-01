const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5001';

export async function POST(req: Request) {
  try {
    const body = await req.json();

    // Validate request
    if (!body.query) {
      return new Response('Invalid request: query required', { status: 400 });
    }

    // URLs are optional - backend will auto-select if not provided
    // Ensure urls is an array if provided, or default to empty array
    if (body.urls !== undefined && (!Array.isArray(body.urls))) {
      return new Response('Invalid request: urls must be an array', { status: 400 });
    }

    // Send request to backend research endpoint
    const backendResponse = await fetch(`${BACKEND_URL}/api/research`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({ error: backendResponse.statusText }));
      throw new Error(`Backend error: ${backendResponse.status} - ${errorData.error || backendResponse.statusText}`);
    }

    const data = await backendResponse.json();
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
    
  } catch (error: any) {
    console.error('Research API error:', error);
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

