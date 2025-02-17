import asyncio as asy
import src.gpt as gpt
import src.search as search
import json as jn
import time
import re

class Searcherer:
    
    """
    content = "<tag>content0</tag>\n<tag1>content1</tag1>"
    output = {
        "tag": "content0",
        "tag1": "content1"
    }
    """
    def _pseudo_html_parser(self, content: str) -> dict[str, str]:
        pattern = r'<([^>]+)>([^<]+)</\1>'
        matches = re.findall(pattern, content)
        return {tag: value.strip() for tag, value in matches}

    def __init__(self, proxy=None, site_maximum=220_000):
        
        self.proxy = proxy
        self.site_maximum = site_maximum
        self.model = gpt.models_stock.claude_3_5_sonnet

        self.mgpt = gpt.Chat(
            model=self.model,
            provider=gpt.provider_stock.PollinationsAI
            # provider=None
        )

        self.persite_gpt = gpt.Chat(
            model=self.model,
            provider=gpt.provider_stock.PollinationsAI
            # provider=None
        )

        self.fanalysis_gpt = gpt.Chat(
            model=self.model,
            provider=gpt.provider_stock.PollinationsAI
            # provider=None
        )

        self.conclusion_gpt = gpt.Chat(
            model=self.model,
            provider=gpt.provider_stock.PollinationsAI
            # provider=None
        )

        self.mgsearch = search.GoogleSearcher()

        self.msystem_prompt = """
Ты - система поиска информации. Отвечай в формате JSON. Разбей ответ на такие пункты:
```
{
    "tasks" : [
    {
        "name": "...",
        "content": "..."
    },
    ...
    ]
}
```
Твоя задача: разбить задачу на несколько под-задач, для дальнейшего подробного исследования. 
Каждая тема должна быть самодостаточна, т.е. не опираться на результаты исследования предыдущих тем, так как они будут рассматриваться отдельно.

В ответе не используй ``` для выделения JSON, пиши сразу в формате JSON. Ответ НЕ в формате JSON ОТКЛОНЯЕТСЯ. Очень важно, чтобы твой ответ ПОЛНОСТЬЮ соответствовал моим требованиям. Не добавляй ничего лишнего
"""
        self.subsearch_system_prompt = """
Тебе дается общая тема и вопрос. Твоя задача составить запрос в гугл, чтобы получить ответ на этот вопрос. Отвечай в формате JSON:

```
{
    "theme": "...",
    "sub_theme": "...",
    "prompt": "...", // Твой запрос в гугл
}
```

В ответе не используй ``` для выделения JSON, пиши сразу в формате JSON. Ответ НЕ в формате JSON ОТКЛОНЯЕТСЯ. Очень важно, чтобы твой ответ ПОЛНОСТЬЮ соответствовал моим требованиям. Не добавляй ничего лишнего. 
"""
        self.persite_system_prompt = """
Тебе дается конкретная тема и содержимое сайта, который был найден по запросу в гугл. 
Тебе нужно составить анализ содержимого этого сайта (выудить информацию, которая полезна для темы). 
Сделай акцент не на структуре и обобщении, а на содержании и практике.
Не обязательно, что сайт пригодиться для анализа темы, для этого, сверяй его с общим вопросом.

Твой ответ должен быть в таком формате:
```
<status>False</status>, // Полезен ли сайт для темы, или нет
<analysis>...</analysis> // Опционально. Если статус true, то это твой анализ
```

Ответ НЕ в запрошенном формате ОТКЛОНЯЕТСЯ. Очень важно, чтобы твой ответ ПОЛНОСТЬЮ соответствовал моим требованиям. Не добавляй ничего лишнего.
"""
        self.finala_system_prompt = """
Тебе дается тема и анализ сайтов, которые были найдены в гугле. 
Тебе нужно составить общий анализ этой темы, основываясь на данных. 
Сделай акцент не на структуре и обобщении, а на содержании и практике, сделай более полный ответ, а не вывод, т.к. тебе нужно дать ответ на вопрос 
(желательно не через указание шагов, которые надо сделать, а именно сами действия. Например написать не `нужно написать такой код, ...`, а `вам нужно написать такой код: ```code```, ... `. Также, но и с другими аспектами, не только с кодом), а не просто сделать вывод. 
Однако не заостряй такое внимание на темах, которые не тесно связаны с первоначальным вопросом. 
(например, если вопрос про то, как использовать чип для достижения Nой цели, не надо писать примеры кода использования этого чипа в других сценариях). 
Не используй первоначальный вопрос в качестве базы для ответа, вместо него только твою суб-тему. 
Вопрос нужен *только* для того, чтобы не выходить за рамки общей темы.
"""
        self.conclusion_system_prompt = """
Сделай вывод по данным анализам тем. Отвечай в формате Markdown. Сделай максимально полный по объему вывод.
"""

    async def search(self, query: str, depth=5, debug=True) -> tuple[str, str, str, list[str]]:
        if debug: print(f"Запрос: {query}")

        theme_name = await self.mgpt.addMessageAsync(
            query=f"Дан текст вопроса: {query}, тебе необходимо ответить его тему, для названия файла ответа. Отвечай только это, не добавляй ничего лишнего"
        )

        if debug: print("\nРазбиение задачи на суб-темы")
        self.mgpt.setSystemQuery(self.msystem_prompt)
        ans = await self.mgpt.addMessageAsync(
            query=f"""Запрос: <{query}>. """
        )
        tasks = jn.loads(ans)["tasks"]
        
        google_results = dict()
        
        if debug: print("\nГугление тем")
        self.mgpt.setSystemQuery(self.subsearch_system_prompt)
        for task in tasks:
            name, question = task["name"], task["content"]
            if debug: print(f"\tТема: {name}, Вопрос: {question}")
            tm = 1.0
            while True:
                try:
                    ans = await self.mgpt.addMessageAsync(
                        query=f"""Имя суб-темы: <{name}>. Вопрос: <{question}>. Общая тема: <{query}>"""
                    )
                    break
                except gpt.g4f.errors.ResponseStatusError as ex:
                    print(f"Error: {ex.args}")
                    time.sleep(tm)
                    tm *= 1.5

            json_ans = jn.loads(ans)
            results = await self.mgsearch.search(
                query=json_ans["prompt"],
                num_results=depth,
                proxy=self.proxy
            )

            google_results[json_ans["sub_theme"]] = results

        # with open("./assets/results.json", "w") as f:
        #     jn.dump(google_results, f, indent=4, ensure_ascii=False)

        google_analysis = dict()

        if debug: print("\nАнализ сайтов")
        self.persite_gpt.setSystemQuery(self.persite_system_prompt)
        for sub_theme, results in google_results.items():
            if debug: print(f"\nСуб-тема: {sub_theme}")
            self.persite_gpt.clearContext()
            google_analysis[sub_theme] = {}
            for site, content in results.items():
                if debug: print(f"\tСайт: {site[:100]}")
                if content == "": continue
                tm = 1.0
                while True:
                    try:
                        ans = await self.persite_gpt.addMessageAsync(
                            query=f"Первоначальный вопрос:<{query}>, Тема: <{sub_theme}>, Сайт: <{site}>, Содержимое:\n\n{content[:self.site_maximum]}"
                        )
                        try:
                            json_ans = self._pseudo_html_parser(ans)
                        except Exception as ex:
                            print(f"Failed to parse pseudo-HTML: {ex}")
                            with open("./sites_failed_{rnd.randint(0, 1000000)}.json", "a") as f:
                                f.write(ans + "\n")
                                continue
                        if json_ans["status"] == "True":
                            google_analysis[sub_theme][site] = json_ans["analysis"]
                        break
                    except gpt.g4f.errors.ResponseStatusError as ex:
                        print(f"Error: {ex.args}")
                        time.sleep(tm)
                        tm *= 1.5
        
        # with open("./assets/analysis.json", "w") as f:
        #     try:
        #         jn.dump(google_analysis, f, indent=4, ensure_ascii=False)
        #     except:
        #         f.write(google_analysis)
        
        final_analysis = dict()

        if debug: print("\nСборка анализов тем")
        self.fanalysis_gpt.setSystemQuery(self.finala_system_prompt)
        for sub_theme, sites in google_analysis.items():
            if debug: print(f"\tСуб-тема: {sub_theme}")
            tm = 1.0
            while True:
                try:
                    final_analysis[sub_theme] = await self.fanalysis_gpt.addMessageAsync(
                        query=f"Первоначальный вопрос:<{query}>, Тема: <{sub_theme}>, Анализ сайтов:\n\n{sites}"
                    )
                    break
                except gpt.g4f.errors.ResponseStatusError as ex:
                    print(f"Error: {ex.args}")
                    time.sleep(tm)
                    tm *= 1.5

        per_site = f"# {query.capitalize()}\n"
        for sub_theme, ans in final_analysis.items():
            per_site += f"## {sub_theme}\n\n"
            per_site += ans + "\n"
        

        if debug: print("\nСборка ответа")

        self.conclusion_gpt.setSystemQuery(self.conclusion_system_prompt)
        final = ""
        while True:
            try:
                final = await self.conclusion_gpt.addMessageAsync(
                    query=f"Первоначальный вопрос: <{query}>, Анализы тем:\n\n{final_analysis}"
                )
                break
            except gpt.g4f.errors.ResponseStatusError as ex:
                print(f"Error: {ex.args}")
                time.sleep(tm)
                tm *= 1.5
        
        return final, per_site, theme_name, [site for (sub_theme, site) in google_analysis.items()]

async def main():
    s = Searcherer()
    # results = await s.mgsearch.search(
    #     query="что такое ai",
    #     num_results=5,
    #     proxy=proxy
    # )
    await s.search("что такое ai")

if __name__ == "__main__":
    asy.run(main())