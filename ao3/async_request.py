# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

from time import time as _time
from random import random as _random

import asyncio as _asyncio
from aiohttp import ClientSession

from drl_typing import *


async def __get_page(
	url: str, session: ClientSession, semaphore: _asyncio.Semaphore,
	print_urls=False,
):
	async with semaphore:
		async with session.get(url) as response:
			status = response.status
			text = await response.text() if status == 200 else ''
			if print_urls:
				print(url)
			return url, status, text


async def __get_page_timed(
	url: str, session: ClientSession, semaphore: _asyncio.Semaphore,
	end_time: _if,
	print_urls=False,
):
	async with semaphore:
		async with session.get(url) as response:
			status = response.status
			text = await response.text() if status == 200 else ''
			time_to_wait = end_time - _time()
			if time_to_wait > 0:
				await _asyncio.sleep(time_to_wait)
			if print_urls:
				print(url)
			return url, status, text


async def __get_all_pages(
	urls: _i_str,
	max_concurrent: int,
	spread_time: _if,
	print_urls=False,
):
	urls = tuple(urls)

	do_limit = max_concurrent > 0

	# plan delays if we need to do them:
	delays = tuple()
	if do_limit and spread_time > 0.1:  # at least, 100 ms
		# generate relative randoms in [0.5, 1.5] range:
		delays = tuple(
			_random() + 0.5
			for _ in range(min(max_concurrent, len(urls)))
		)
		random_total: float = sum(delays)
		normalizer = spread_time / random_total
		delays = tuple(d * normalizer for d in delays)

	if not do_limit:
		max_concurrent = len(urls) + 1

	semaphore = _asyncio.Semaphore(max_concurrent)
	async with ClientSession() as session:
		tasks = list()
		# use tmp iterator to select first N urls for timed, then keep the rest.
		# the size of urls is guaranteed to be not less then delays.
		urls_iter = iter(urls)
		start_time = _time()
		tasks.extend(
			_asyncio.create_task(__get_page_timed(
				next(urls_iter), session, semaphore, start_time + delay, print_urls
			))
			for delay in delays
		)
		urls = tuple(urls_iter)  # pass the left urls back

		tasks.extend(
			_asyncio.create_task(__get_page(url, session, semaphore, print_urls))
			for url in urls
		)
		return await _asyncio.gather(*tasks)


def get_pages(
	urls: _i_str,
	max_concurrent: int = 20,
	spread_time: _if = 13.7,  # about 10 seconds, but not round
	print_urls=False,
):
	"""
	Load html from urls asynchronously.

	:param max_concurrent:
		Lets you limit how many workers perform page load concurrently. 0 - no limit.
	:param spread_time:
		When workers limit provided, distibute the first bunch across this many
		seconds. Expected time of completion is intentionally slightly random for
		each of those workers.
	:param print_urls:
		Print each page url when it's finished loading.
	"""
	res: _l[_tpl[str, int, str]] = _asyncio.run(__get_all_pages(
		urls, max_concurrent, spread_time, print_urls
	))
	return res
