import { NextRequest, NextResponse } from "next/server";

const API_URL = (
  process.env.MEDAI_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000"
).replace(/\/$/, "");
const API_KEY = process.env.MEDAI_WEB_API_KEY;

function jsonError(detail: string, status: number, extra: Record<string, unknown> = {}) {
  return NextResponse.json({ detail, ...extra }, { status });
}

export async function POST(request: NextRequest) {
  if (!API_KEY) {
    return jsonError(
      "The MedAI web service is not configured with MEDAI_WEB_API_KEY.",
      503,
    );
  }

  const incoming = await request.formData();
  const imageType = incoming.get("image_type");
  const file = incoming.get("file");

  if (typeof imageType !== "string" || !(file instanceof File)) {
    return jsonError("image_type and file are required.", 400);
  }

  if (imageType !== "xray" && imageType !== "skin") {
    return jsonError("image_type must be 'xray' or 'skin'.", 400);
  }

  const form = new FormData();
  form.append("file", file, file.name);

  let response: Response;
  try {
    response = await fetch(
      `${API_URL}/api/v1/predict?image_type=${encodeURIComponent(imageType)}`,
      {
        method: "POST",
        headers: { "X-API-Key": API_KEY },
        body: form,
        cache: "no-store",
      },
    );
  } catch (error) {
    return jsonError(
      "The web service could not reach the MedAI API.",
      502,
      { api_url: API_URL, reason: error instanceof Error ? error.message : String(error) },
    );
  }

  const body = await response.text();
  const contentType = response.headers.get("content-type") ?? "";

  if (!response.ok) {
    let detail = body.trim() || "MedAI API request failed.";
    if (contentType.includes("application/json")) {
      try {
        const parsed = JSON.parse(body) as { detail?: string };
        detail = parsed.detail ?? detail;
      } catch {
        // Keep the raw response as diagnostic text.
      }
    }

    return jsonError(
      detail,
      response.status,
      { upstream_status: response.status, upstream_content_type: contentType || "unknown" },
    );
  }

  if (!contentType.includes("application/json")) {
    return jsonError(
      "The MedAI API returned an unexpected non-JSON response.",
      502,
      { upstream_status: response.status, upstream_body: body.slice(0, 500) },
    );
  }

  return new NextResponse(body, {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}
