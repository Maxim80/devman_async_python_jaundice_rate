from aiohttp import web, ClientSession
from anyio import create_task_group
from main import get_charged_worlds, process_article
import pymorphy2


ARTICLES_LIMIT = 10


class NoDataInQuery(Exception):
    pass


class ExceedingNumberOfRequests(Exception):
    pass


def pack_query_to_list(query):
    if not query:
        raise NoDataInQuery
    results = query.split(',')
    if len(results) > ARTICLES_LIMIT:
        raise ExceedingNumberOfRequests
    return [res.strip() for res in results]


async def process_article_wrapper(urls):
    morph = pymorphy2.MorphAnalyzer()
    charged_words = await get_charged_worlds()
    processing_results = []
    async with ClientSession() as session:
        async with create_task_group() as task_group:
            for url in urls:
                await task_group.spawn(process_article, session, morph, charged_words, url, processing_results)

    return processing_results


async def handle(request):
    try:
        query = request.query.get('urls')
        query_values = pack_query_to_list(query)

    except (KeyError, NoDataInQuery):
        return web.json_response({'error': 'No data in query.'})

    except ExceedingNumberOfRequests:
        return web.json_response({"error": "too many urls in request, should be 10 or less"})

    json_data = await process_article_wrapper(query_values)
    return web.json_response(json_data)


app = web.Application()
app.add_routes([
    web.get('/', handle)
])


if __name__ == '__main__':
    web.run_app(app)
