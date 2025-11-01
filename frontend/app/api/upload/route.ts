export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    
    // Get all files (supporting multiple file uploads)
    const files = formData.getAll('file') as File[];

    if (!files || files.length === 0 || (files.length === 1 && !files[0])) {
      return new Response(JSON.stringify({ error: 'No files provided' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5001';

    // Create FormData for backend with all files
    const backendFormData = new FormData();
    
    // Append all files with the same key 'file' (backend uses getlist('file'))
    files.forEach((file) => {
      if (file) {
        backendFormData.append('file', file);
      }
    });

    // Forward to Flask backend
    const response = await fetch(`${backendUrl}/api/upload`, {
      method: 'POST',
      body: backendFormData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: response.statusText }));
      return new Response(JSON.stringify(errorData), {
        status: response.status,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const data = await response.json();
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error: any) {
    console.error('Upload API error:', error);
    return new Response(
      JSON.stringify({ error: error.message || 'Internal server error' }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

