import { NextResponse } from 'next/server';

export async function GET(
  _request: Request,
  { params }: { params: { id: string } }
) {
  const devisId = params.id;

  const backendUrl =
    (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') +
    `/api/chat/devis/${devisId}/pdf`;

  try {
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: { 'Accept': 'application/pdf' },
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: `Erreur backend: ${response.status} - ${errorText}` },
        { status: response.status }
      );
    }

    const pdfBuffer = await response.arrayBuffer();

    return new NextResponse(pdfBuffer, {
      status: 200,
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="devis-${devisId}.pdf"`,
        'Content-Length': pdfBuffer.byteLength.toString(),
      },
    });
  } catch (e) {
    return NextResponse.json({ error: 'Erreur serveur', details: e }, { status: 500 });
  }
}
