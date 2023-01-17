""" meval """

# Copyright (C) 2020-2022 by UsergeTeam@Github, < https://github.com/UsergeTeam >.
# Copyright (C) 2023 by wulan17@Github, < https://github.com/wulan17 >.
#
# This file is part of < https://github.com/UsergeTeam/Userge > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/UsergeTeam/Userge/blob/master/LICENSE >
#
# All rights reserved.

import asyncio
import inspect
import io
import os
import pyrogram
import re
import sys
import time
import traceback
import uuid

from html import escape
from meval import meval
from typing import Any, Optional, Tuple, Union
from userge import userge, Message

def usec() -> int:
    """Returns the current time in microseconds since the Unix epoch."""

    return int(time.time() * 1000000)

def format_duration_us(t_us: Union[int, float]) -> str:
    """Formats the given microsecond duration as a string."""

    t_us = int(t_us)

    t_ms = t_us / 1000
    t_s = t_ms / 1000
    t_m = t_s / 60
    t_h = t_m / 60
    t_d = t_h / 24

    if t_d >= 1:
        rem_h = t_h % 24
        return "%dd %dh" % (t_d, rem_h)

    if t_h >= 1:
        rem_m = t_m % 60
        return "%dh %dm" % (t_h, rem_m)

    if t_m >= 1:
        rem_s = t_s % 60
        return "%dm %ds" % (t_m, rem_s)

    if t_s >= 1:
        return "%d sec" % t_s

    if t_ms >= 1:
        return "%d ms" % t_ms

    return "%d μs" % t_us


@userge.on_cmd("meval", about={
    'header': "Meval",
    'description': "Evaluate code",
    'usage': "{tr}meval [code]"})
async def cmd_eval(message: Message):
	text = message.text.split(None,1)
	if len(text) < 2:
		return "Give me code to evaluate."
	code = text[1]

	out_buf = io.StringIO()

	async def _eval() -> Tuple[str, Optional[str]]:
		# Message sending helper for convenience
		async def send(*args: Any, **kwargs: Any) -> pyrogram.types.Message:
			return await message.reply_text(*args, **kwargs)

		# Print wrapper to capture output
		# We don't override sys.stdout to avoid interfering with other output
		def _print(*args: Any, **kwargs: Any) -> None:
			if "file" not in kwargs:
				kwargs["file"] = out_buf

			return print(*args, **kwargs)

		eval_vars = {
			# Contextual info
			"loop": userge.loop,
			"c": userge,
			"client": userge,
			"stdout": out_buf,
			# Convenience aliases
			"m": message,
			"msg": message,
			"message": message,
			# Helper functions
			"send": send,
			"print": _print,
			# Built-in modules
			"inspect": inspect,
			"os": os,
			"re": re,
			"sys": sys,
			"traceback": traceback,
			# Third-party modules
			"pyrogram": pyrogram
		}

		try:
			return "", await meval(code, globals(), **eval_vars)
		except Exception as e:  # skipcq: PYL-W0703
			# Find first traceback frame involving the snippet
			first_snip_idx = -1
			tb = traceback.extract_tb(e.__traceback__)
			for i, frame in enumerate(tb):
				if frame.filename == "<string>" or frame.filename.endswith("ast.py"):
					first_snip_idx = i
					break

			# Re-raise exception if it wasn't caused by the snippet
			if first_snip_idx == -1:
				raise e

			# Return formatted stripped traceback
			stripped_tb = tb[first_snip_idx:]
			formatted_tb = util.error.format_exception(e, tb=stripped_tb)
			return "⚠️ Error executing snippet\n\n", formatted_tb

	before = usec()
	prefix, result = await _eval()
	after = usec()

	# Always write result if no output has been collected thus far
	if not out_buf.getvalue() or result is not None:
		print(result, file=out_buf)

	el_us = after - before
	el_str = format_duration_us(el_us)

	out = out_buf.getvalue()
	# Strip only ONE final newline to compensate for our message formatting
	if out.endswith("\n"):
		out = out[:-1]

	result = f"""{prefix}<b>In:</b>
<pre language="python">{escape(code)}</pre>
<b>Out:</b>
<pre language="python">{escape(out)}</pre>
Time: {el_str}"""

	if len(result) > 4096:
		with io.BytesIO(str.encode(out)) as out_file:
			out_file.name = str(uuid.uuid4()).split("-")[0].upper() + ".TXT"
			caption = f"""{prefix}<b>In:</b>
<pre language="python">{escape(code)}</pre>"""
			await message.reply_document(
				document=out_file, caption=caption, disable_notification=True,parse_mode=pyrogram.enums.parse_mode.ParseMode.HTML
			)
		return None

	await message.edit_text(
		result,
		parse_mode=pyrogram.enums.parse_mode.ParseMode.HTML,
	)
