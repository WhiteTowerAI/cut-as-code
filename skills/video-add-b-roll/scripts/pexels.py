"""Safely acquire local and Pexels B-roll candidates."""

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "video-understand" / "scripts"))
import projectlib


PEXELS_API = "https://api.pexels.com/v1/videos/search"
USER_AGENT = "cut-as-code-video-add-b-roll/1.0"
LICENSE_URL = "https://www.pexels.com/license/"
TERMS_URL = "https://www.pexels.com/terms-of-service/"
VIDEO_HOSTS = {"videos.pexels.com"}
API_HOSTS = {"api.pexels.com"}
PAGE_HOSTS = {"www.pexels.com"}


def validate_url(value, allowed_hosts):
    """Return an HTTPS URL with an exact permitted host."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid URL") from exc
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or parsed.username or parsed.password or
            host not in set(allowed_hosts) or port not in (None, 443)):
        raise ValueError("URL is not an allowed HTTPS endpoint")
    return urlunsplit(("https", host, parsed.path or "/", parsed.query, ""))


def _now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _open(opener, request, allowed_hosts, timeout=30):
    handler = opener if opener is not None else _default_opener(allowed_hosts)
    return handler.open(request, timeout=timeout) if hasattr(handler, "open") else handler(request, timeout=timeout)


class _RedirectLimit(HTTPRedirectHandler):
    max_redirections = 3

    def __init__(self, allowed_hosts):
        super().__init__()
        self.allowed_hosts = frozenset(allowed_hosts)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, self.allowed_hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _default_opener(allowed_hosts): return build_opener(_RedirectLimit(allowed_hosts))


def _matches_orientation(width, height, orientation):
    return width > height if orientation == "landscape" else height > width if orientation == "portrait" else width == height


def _variant(item, url):
    return {
        "file_id": item["id"],
        "download_url": url,
        "width": item["width"],
        "height": item["height"],
    }


def search_videos(query, *, orientation="landscape", per_page=10, api_key=None, opener=None):
    if not isinstance(query, str) or not query.strip(): raise ValueError("query is required")
    if orientation not in {"landscape", "portrait", "square"}: raise ValueError("invalid orientation")
    if not isinstance(per_page, int) or isinstance(per_page, bool) or not 1 <= per_page <= 80: raise ValueError("per_page must be 1..80")
    key = api_key or os.environ.get("PEXELS_API_KEY")
    if not key: raise ValueError("Pexels API key is required")
    request = Request(f"{PEXELS_API}?{urlencode({'query': query, 'orientation': orientation, 'per_page': per_page})}", headers={"Authorization": key, "Accept": "application/json", "User-Agent": USER_AGENT})
    with _open(opener, request, API_HOSTS) as response:
        validate_url(response.geturl(), API_HOSTS)
        try: payload = json.loads(response.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise ValueError("invalid Pexels response") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("videos"), list): raise ValueError("invalid Pexels response")
    records, seen_videos, seen_files = [], set(), set()
    for video in payload["videos"]:
        if not isinstance(video, dict): continue
        video_id = video.get("id")
        if not isinstance(video_id, int) or isinstance(video_id, bool) or video_id <= 0 or video_id in seen_videos: continue
        duration, width, height = video.get("duration"), video.get("width"), video.get("height")
        if not isinstance(duration, (int, float)) or duration <= 0 or not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0: continue
        try: source_url = validate_url(video.get("url"), PAGE_HOSTS)
        except ValueError: continue
        choices, local_file_ids = [], set()
        files = video.get("video_files", [])
        if not isinstance(files, list): continue
        for item in files:
            if not isinstance(item, dict): continue
            file_id = item.get("id")
            if not isinstance(file_id, int) or isinstance(file_id, bool) or file_id <= 0: continue
            file_key = (video_id, file_id)
            if file_key in seen_files or file_id in local_file_ids: continue
            try: url = validate_url(item.get("link"), VIDEO_HOSTS)
            except ValueError: continue
            iw, ih = item.get("width"), item.get("height")
            if isinstance(iw, int) and isinstance(ih, int) and iw > 0 and ih > 0 and _matches_orientation(iw, ih, orientation):
                local_file_ids.add(file_id)
                choices.append((iw * ih, file_id, item, url))
        if not choices: continue
        _, _, item, url = max(choices, key=lambda value: (value[0], value[1]))
        qualifying = [choice for choice in choices if min(choice[2]["width"], choice[2]["height"]) >= 480]
        analysis_choice = min(qualifying, key=lambda value: (value[0], value[1])) if qualifying else max(choices, key=lambda value: (value[0], value[1]))
        _, _, analysis_item, analysis_url = analysis_choice
        seen_videos.add(video_id); seen_files.update((video_id, choice[2]["id"]) for choice in choices)
        creator = video.get("user", {}).get("name") if isinstance(video.get("user"), dict) else None
        delivery_variant = _variant(item, url)
        analysis_variant = _variant(analysis_item, analysis_url)
        records.append({"id": f"{video['id']}-{item['id']}", "provider_id": video["id"], "file_id": item["id"], "media_type": "video", "download_url": url, "width": item["width"], "height": item["height"], "duration_s": duration, "analysis_variant": analysis_variant, "delivery_variant": delivery_variant, "provenance": {"source_type": "pexels", "provider_id": video["id"], "source_url": source_url, "creator": creator or "Pexels creator", "license": "Pexels License", "license_url": LICENSE_URL, "terms_url": TERMS_URL, "retrieval_time": _now(), "download_url": url, "dimensions": {"width": item["width"], "height": item["height"]}, "duration_s": duration}})
    return records


def variant_candidate(candidate, role):
    if role not in {"analysis", "delivery"}:
        raise ValueError("variant role must be analysis or delivery")
    if not isinstance(candidate, dict) or candidate.get("provenance", {}).get("source_type") != "pexels":
        raise ValueError("variant candidate must be a Pexels record")
    variant = candidate.get(f"{role}_variant")
    if not isinstance(variant, dict):
        raise ValueError(f"candidate has no {role} variant")
    required = ("file_id", "download_url", "width", "height")
    if any(field not in variant for field in required):
        raise ValueError(f"candidate {role} variant is incomplete")
    provider_id, file_id = candidate.get("provider_id"), variant.get("file_id")
    width, height = variant.get("width"), variant.get("height")
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in (provider_id, file_id, width, height)):
        raise ValueError(f"candidate {role} variant identifiers or dimensions are invalid")
    download_url = validate_url(variant.get("download_url"), VIDEO_HOSTS)
    provenance = candidate.get("provenance")
    if (not isinstance(provenance, dict) or provenance.get("provider_id") != provider_id
            or validate_url(provenance.get("source_url"), PAGE_HOSTS) != provenance.get("source_url")
            or provenance.get("license_url") != LICENSE_URL or provenance.get("terms_url") != TERMS_URL):
        raise ValueError("candidate Pexels provenance is invalid")
    result = copy.deepcopy(candidate)
    result.update({field: variant[field] for field in required})
    result["download_url"] = download_url
    result["variant_role"] = role
    result["provenance"]["download_url"] = result["download_url"]
    result["provenance"]["dimensions"] = {"width": result["width"], "height": result["height"]}
    return result


def probe_media(path):
    path = Path(path)
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        stream = next(item for item in data.get("streams", []) if item.get("codec_type") == "video")
        duration = float(stream.get("duration") or data.get("format", {}).get("duration"))
        width, height = int(stream["width"]), int(stream["height"])
        if duration <= 0 or width <= 0 or height <= 0: raise ValueError("invalid video metadata")
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "null", "-"], capture_output=True, check=True)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError, StopIteration) as exc:
        raise ValueError("media is not a decodable video") from exc
    return {"duration_s": duration, "width": width, "height": height, "codec": stream.get("codec_name")}


def _cache_destination(destination, purpose="delivery"):
    if purpose not in {"delivery", "analysis"}:
        raise ValueError("invalid cache purpose")
    target = Path(destination).resolve()
    expected = ("work", "cache", "b-roll", "candidates") if purpose == "delivery" else ("work", "cache", "b-roll", "candidate-analysis", "media")
    for parent in (target.parent, *target.parents):
        if parent.parts[-len(expected):] == expected:
            try: target.relative_to(parent)
            except ValueError: break
            if target.parent == parent and target.name and target.name not in {".", ".."}: return target
    raise ValueError(f"destination must be directly beneath {'/'.join(expected)}")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def _record(candidate, target, probe, digest=None):
    result = dict(candidate)
    result.update({"path": target, "cache_path": candidate.get("cache_path", target.as_posix()), "sha256": digest or _sha256(target), "bytes": target.stat().st_size, "probe": probe})
    return result


def download_candidate(candidate, destination, *, opener=None, max_bytes=250_000_000, retries=3, purpose="delivery"):
    if not isinstance(candidate, dict) or not isinstance(candidate.get("download_url"), str): raise ValueError("candidate download_url is required")
    if not isinstance(max_bytes, int) or max_bytes <= 0 or not isinstance(retries, int) or retries < 1: raise ValueError("invalid download limits")
    target = _cache_destination(destination, purpose=purpose); target.parent.mkdir(parents=True, exist_ok=True); part = target.with_name(target.name + ".part")
    url = validate_url(candidate["download_url"], VIDEO_HOSTS)
    expected = candidate.get("sha256")
    if target.exists() and isinstance(expected, str) and _sha256(target) == expected:
        try: return _record(candidate, target, probe_media(target), expected)
        except ValueError: target.unlink()
    elif target.exists():
        target.unlink()
    for attempt in range(retries):
        offset = part.stat().st_size if part.exists() else 0
        headers = {"User-Agent": USER_AGENT, **({"Range": f"bytes={offset}-"} if offset else {})}
        request = Request(url, headers=headers)
        try:
            with _open(opener, request, VIDEO_HOSTS) as response:
                final_url = validate_url(response.geturl(), VIDEO_HOSTS)
                status = getattr(response, "status", response.getcode() if hasattr(response, "getcode") else 200)
                headers = response.headers
                length = headers.get("Content-Length")
                if length is not None and not str(length).isdigit(): raise ValueError("invalid Content-Length")
                length = int(length) if length is not None else None
                range_total = None
                if status == 206:
                    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", str(headers.get("Content-Range", "")))
                    if not match: raise ValueError("invalid Content-Range")
                    start, end, range_total = map(int, match.groups()); span = end - start + 1
                    if start != offset or end < start or range_total <= end or end != range_total - 1 or range_total > max_bytes: raise ValueError("invalid Content-Range")
                    if length is not None and length != span: raise ValueError("Content-Length does not match range")
                    expected_bytes = span
                    mode = "ab"
                elif offset and status == 200: mode = "wb"; offset = 0
                elif status != 200: raise ValueError("unexpected download status")
                else: mode = "wb"
                if status == 200:
                    if length is not None and length > max_bytes: raise ValueError("download exceeds limit")
                    expected_bytes = length
                total, response_bytes = offset, 0
                with open(part, mode) as handle:
                    while chunk := response.read(1024 * 1024):
                        response_bytes += len(chunk); total += len(chunk)
                        if total > max_bytes: raise ValueError("download exceeds limit")
                        handle.write(chunk)
                if expected_bytes is not None and response_bytes != expected_bytes: raise ValueError("download is incomplete")
                if range_total is not None and part.stat().st_size != range_total: raise ValueError("range download is incomplete")
                candidate = copy.deepcopy(candidate)
                provenance = candidate.get("provenance")
                if isinstance(provenance, dict) and provenance.get("source_type") == "pexels":
                    provenance["download_url"] = final_url
                candidate["download_url"] = final_url
            try: probe = probe_media(part)
            except Exception: part.unlink(missing_ok=True); raise
            try: digest = _sha256(part)
            except Exception: part.unlink(missing_ok=True); raise
            os.replace(part, target)
            return _record(candidate, target, probe, digest)
        except HTTPError as exc:
            if exc.code not in {408, 429, 500, 502, 503, 504}:
                part.unlink(missing_ok=True); raise
            if attempt + 1 == retries: raise
        except URLError:
            if attempt + 1 == retries: raise
        except ValueError:
            part.unlink(missing_ok=True); raise
    raise RuntimeError("download attempts exhausted")


def import_local(source, destination, provenance, *, max_bytes=250_000_000):
    source, target = Path(source), _cache_destination(destination)
    if not source.is_file(): raise ValueError("source file is required")
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0: raise ValueError("max_bytes must be a positive integer")
    if source.stat().st_size > max_bytes: raise ValueError("source exceeds limit")
    if not isinstance(provenance, dict) or provenance.get("source_type") not in {"local", "external-generated"}: raise ValueError("invalid provenance")
    if not all(isinstance(provenance.get(key), str) and provenance[key].strip() for key in ("creator", "license", "retrieval_time")): raise ValueError("provenance is incomplete")
    generated = provenance["source_type"] == "external-generated"
    if generated and (not all(provenance.get(key) for key in ("generation_provider", "generation_model")) or not (provenance.get("prompt") or provenance.get("job_id"))): raise ValueError("generated provenance is incomplete")
    target.parent.mkdir(parents=True, exist_ok=True); part = target.with_name(target.name + ".part")
    try:
        total = 0
        with open(source, "rb") as incoming, open(part, "wb") as outgoing:
            while chunk := incoming.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes: raise ValueError("source exceeds limit")
                outgoing.write(chunk)
        probe = probe_media(part); digest = _sha256(part); os.replace(part, target)
    except Exception:
        part.unlink(missing_ok=True); raise
    clean_provenance = dict(provenance); clean_provenance["original_path"] = source.resolve().as_posix()
    return _record({"id": target.stem, "media_type": "video", "provenance": clean_provenance}, target, probe, digest)


def _json(value): return json.dumps(value, default=lambda item: item.as_posix() if isinstance(item, Path) else (_ for _ in ()).throw(TypeError()), indent=2)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if any(value == "--api-key" or value.startswith("--api-key=") for value in argv):
        print("Pexels API key must be set in PEXELS_API_KEY", file=sys.stderr)
        raise SystemExit(2)
    parser = argparse.ArgumentParser(); commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search"); search.add_argument("query"); search.add_argument("--orientation", default="landscape"); search.add_argument("--per-page", type=int, default=10)
    download = commands.add_parser("download"); download.add_argument("candidate_json"); download.add_argument("destination"); download.add_argument("--variant", choices=("analysis", "delivery"))
    local = commands.add_parser("import-local"); local.add_argument("source"); local.add_argument("destination"); local.add_argument("provenance_json")
    args = parser.parse_args(argv)
    if args.command == "search": value = search_videos(args.query, orientation=args.orientation, per_page=args.per_page)
    elif args.command == "download":
        candidate = projectlib.load_json(args.candidate_json)
        if args.variant:
            candidate = variant_candidate(candidate, args.variant)
        value = download_candidate(candidate, args.destination, purpose="analysis" if args.variant == "analysis" else "delivery")
    else: value = import_local(args.source, args.destination, projectlib.load_json(args.provenance_json))
    print(_json(value))


if __name__ == "__main__": main()
