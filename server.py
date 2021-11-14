from aiohttp import web, ClientSession
from anyio import create_task_group
from main import get_charged_worlds, process_article
import pymorphy2


class NoDataInQuery(Exception):
    pass


def pack_query_to_list(query):
    if not query:
        raise NoDataInQuery
    return query.split(',')


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

    json_data = await process_article_wrapper(query_values)
    return web.json_response(json_data)


app = web.Application()
app.add_routes([
    web.get('/', handle)
])


if __name__ == '__main__':
    web.run_app(app)

"""
http://0.0.0.0:8080?urls=https://inosmi.ru/economic/20211105/250847958.html,https://inosmi.ru/economic/20211104/250846376.html,https://inosmi.ru/social/20211110/250870936.html,https://inosmi.ru/social/20211110/250867022.html,https://inosmi.ru/social/20211110/250865347.html,https://inosmi.ru/not/exist.html,https://lenta.ru/brief/2021/08/26/afg_terror/

"""
