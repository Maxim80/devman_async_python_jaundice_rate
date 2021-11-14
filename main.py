from adapters import SANITIZERS
from text_tools import split_by_words, calculate_jaundice_rate
from anyio import create_task_group
from urllib.parse import urlparse
from contextlib import contextmanager
import aiohttp
import asyncio
import async_timeout
import aiofiles
import pymorphy2
import os
import logging
import time


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('root')


@contextmanager
def time_completion_contextmanager():
    start = time.monotonic()
    try:
        yield
    finally:
        msg = f'Анализ закончен за {round(time.monotonic() - start)} сек'
        logger.info(msg)


def get_adapter(url):
    domain = urlparse(url).netloc
    adapter_name = domain.replace('.', '_')
    adapter = SANITIZERS[adapter_name]
    return adapter


def packing_into_dict(url, status, score, words_count):
    return {
        'url': url,
        'status': status,
        'score': score,
        'words_count': words_count,
    }


async def get_charged_worlds():
    charged_words = []
    file_names = os.listdir('./charged_dict')
    for file_name in file_names:
        async with aiofiles.open(f'./charged_dict/{file_name}') as f:
            words = await f.readlines()

        charged_words.extend(words)

    return charged_words


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(session, morph, charged_words, url, processing_results):
    try:
        async with async_timeout.timeout(3):
            html = await fetch(session, url)

        adapter = get_adapter(url)

    except asyncio.exceptions.TimeoutError:
        processing_results.append(packing_into_dict(url, 'TIMEOUT', None, None))

    except aiohttp.client_exceptions.ClientResponseError:
        processing_results.append(packing_into_dict(url, 'FETCH_ERROR', None, None))

    except KeyError:
        processing_results.append(packing_into_dict(url, 'PARSING_ERROR', None, None))

    else:
        article_text = adapter(html, plaintext=True)
        with time_completion_contextmanager():
            separated_words = await split_by_words(morph, article_text)
            score = calculate_jaundice_rate(separated_words, charged_words)

        words_count = len(separated_words)
        processing_results.append(packing_into_dict(url, 'OK', score, words_count))



async def main(test_articles):
    morph = pymorphy2.MorphAnalyzer()
    charged_words = await get_charged_worlds()
    processing_results = []
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as task_group:
            for url_article in test_articles:
                await task_group.spawn(process_article, session, morph, charged_words, url_article, processing_results)

    print(*processing_results)



if __name__ == '__main__':
    test_articles = [
            'https://inosmi.ru/economic/20211105/250847958.html',
            'https://inosmi.ru/economic/20211104/250846376.html',
            'https://inosmi.ru/social/20211110/250870936.html',
            'https://inosmi.ru/social/20211110/250867022.html',
            'https://inosmi.ru/social/20211110/250865347.html',
            'https://inosmi.ru/not/exist.html',
            'https://lenta.ru/brief/2021/08/26/afg_terror/',
        ]
    asyncio.run(main(test_articles))
