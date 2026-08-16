const GITHUB_PAGES_ORIGIN = "https://philipstathis.github.io";
const GITHUB_PAGES_PATH_PREFIX = "/niko-chore-balance";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const originUrl = `${GITHUB_PAGES_ORIGIN}${GITHUB_PAGES_PATH_PREFIX}${url.pathname}${url.search}`;
    const response = await fetch(originUrl, {
      method: request.method,
      headers: request.headers,
    });

    if (!/\.(jpe?g|png)$/i.test(url.pathname)) {
      return response;
    }

    const filename = url.pathname.split("/").pop();
    const headers = new Headers(response.headers);
    headers.set("Content-Disposition", `attachment; filename=${filename}`);
    headers.set("Cache-Control", "no-cache");

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  },
};
