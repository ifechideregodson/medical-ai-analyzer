import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.MEDAI_WEB_API_KEY;

export async function POST(request: NextRequest) {
  if (!API_KEY) {
    return NextResponse.json(
      { detail: "The MedAI web service is not configured with a server API key." },
      { status: 503 },
    );
  }

  const incoming = await request.formData();
  const imageType = incoming.get("image_type");
  const file = incoming.get("file");

  if (typeof imageType !== "string" || !(file instanceof File)) {
    return NextResponse.json(
      { detail: "image_type and file are required." },
      { status: 400 },
    );
  }

  const form = new FormData();
  form.append("file", file, file.name);

  const response = await fetch(
    `${API_URL}/api/v1/predict?image_type=${encodeURIComponent(imageType)}`,
    {
      method: "POST",
      headers: { "X-API-Key": API_KEY },
      body: form,
      cache: "no-store",
    },
  );

  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
  });
}
