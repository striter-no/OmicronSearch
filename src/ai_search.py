import asyncio as asy
import src.gpt as gpt
import src.search as search
import random as rnd
import json as jn
import time
import re

from typing import Union

async def asyPrint(msg):
    print(msg)

class Searcherer:
    
    """
    content = "<tag>content0</tag>\n<tag1>content1</tag1>"
    output = {
        "tag": "content0",
        "tag1": "content1"
    }
    """
    def xml_parser(self, content: str) -> dict[str, Union[str, dict]]:
        # Remove leading/trailing whitespace and normalize newlines
        content = content.strip().replace('\n', '')
        
        # Pattern to match tags with their content
        pattern = r'<([^>]+)>(.*?)</\1>'
        matches = re.findall(pattern, content)
        
        result = {}
        for tag, inner_content in matches:
            # If inner content contains tags, parse recursively
            if re.search(r'<[^>]+>', inner_content):
                result[tag] = self.xml_parser(inner_content)
            else:
                result[tag] = inner_content.strip()
        
        return result

    def __init__(self, model=gpt.models_stock.gpt_4o, proxy=None, site_maximum=220_000):
        
        self.proxy = proxy
        self.site_maximum = site_maximum
        self.model = model

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
Ты - система поиска информации. Отвечай в заданном формате. Разбей ответ на такие пункты:
```
<tasks>
<...> // Имя задачи (читабельное, на русском)
    ... // Вопрос, который надо исследовать
</...> // Имя задачи
... // Другие задачи, по такому же принципу
</tasks>
```
Твоя задача: разбить задачу на несколько под-задач, для дальнейшего подробного исследования. 
Каждая тема должна быть самодостаточна, т.е. не опираться на результаты исследования предыдущих тем, так как они будут рассматриваться отдельно.

В ответе не используй ``` для выделения кода, пиши сразу в предоставленном формате.. Ответ НЕ в данном формате ОТКЛОНЯЕТСЯ. Очень важно, чтобы твой ответ ПОЛНОСТЬЮ соответствовал моим требованиям. Не добавляй ничего лишнего
"""
        self.subsearch_system_prompt = """
Тебе дается общая тема и вопрос. Твоя задача составить запрос в гугл, чтобы получить ответ на этот вопрос. Отвечай в формате JSON:

```
<theme>...</theme> // Тема вопроса
<sub_theme>...</sub_theme> // Под тема
<prompt>...</prompt> // Твой запрос в гугл
```

В ответе не используй ``` для выделения кода, пиши сразу в предоставленном формате.. Ответ НЕ в данном формате ОТКЛОНЯЕТСЯ. Очень важно, чтобы твой ответ ПОЛНОСТЬЮ соответствовал моим требованиям. Не добавляй ничего лишнего
"""
        self.persite_system_prompt = """
Тебе дается конкретная тема и содержимое сайта, который был найден по запросу в гугл. 
Тебе нужно составить анализ содержимого этого сайта (выудить информацию, которая полезна для темы). 
Сделай акцент не на структуре и обобщении, а на содержании и практике. 
Хорошо будет, если ты сможешь привести конкретные примеры и цифры из текста.
Не обязательно, что сайт пригодиться для анализа темы, для этого, сверяй его с общим вопросом.

Твой ответ должен быть в таком формате:
```
<analysis>...</analysis> // Анализ сайта
<status>False</status> // Полезен ли сайт для темы, или нет
```

Убери ``` из своего ответа. Ответ НЕ в запрошенном формате ОТКЛОНЯЕТСЯ. Очень важно, чтобы твой ответ ПОЛНОСТЬЮ соответствовал моим требованиям. Не добавляй ничего лишнего.
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

    async def search(self, query: str, depth=5, debug=True, debugHandler = asyPrint) -> tuple[str, str, str, list[str]]:
        if debug: await debugHandler(f"Запрос: {query}")

        theme_name = await self.mgpt.addMessageAsync(
            query=f"Дан текст вопроса: {query}, тебе необходимо ответить его тему, для названия файла ответа. Отвечай только это, не добавляй ничего лишнего"
        )

        if debug: await debugHandler("\nРазбиение задачи на суб-темы")
        self.mgpt.setSystemQuery(self.msystem_prompt)
        ans = await self.mgpt.addMessageAsync(
            query=f"""Запрос: <{query}>. """
        )
        print(ans)

        tasks = []
        xml_tasks = self.xml_parser(ans)
        for task in xml_tasks["tasks"]:
            tasks.append({
                "name": task,
                "content": xml_tasks["tasks"][task],
            })
        
        google_results = dict()
        
        if debug: await debugHandler("\nГугление тем")
        self.mgpt.setSystemQuery(self.subsearch_system_prompt)
        for task in tasks:
            name, question = task["name"], task["content"]
            if debug: await debugHandler(f"\tТема: {name}, Вопрос: {question}")
            tm = 1.0
            while True:
                try:
                    ans = await self.mgpt.addMessageAsync(
                        query=f"""Имя суб-темы: <{name}>. Вопрос: <{question}>. Общая тема: <{query}>"""
                    )
                    break
                except gpt.g4f.errors.ResponseStatusError as ex:
                    print(f"[0] Error: {ex.args}")
                    time.sleep(tm)
                    tm *= 1.5
                except Exception as ex:
                    print(f"[0] Undefinded Error: {ex}")
                    time.sleep(tm)

            json_ans = self.xml_parser(ans)
            print(json_ans)
            results = await self.mgsearch.search(
                query=json_ans["prompt"],
                num_results=depth,
                proxy=self.proxy
            )

            google_results[json_ans["sub_theme"]] = results

        # with open("./assets/results.json", "w") as f:
        #     jn.dump(google_results, f, indent=4, ensure_ascii=False)

        google_analysis = dict()
        sources = []

        if debug: await debugHandler("\nАнализ сайтов")
        self.persite_gpt.setSystemQuery(self.persite_system_prompt)
        for sub_theme, results in google_results.items():
            if debug: await debugHandler(f"\nСуб-тема: {sub_theme}")
            google_analysis[sub_theme] = {}
            for site, content in results.items():
                self.persite_gpt.clearContext()
                if debug: await debugHandler(f"\tСайт: {site[:100]}")
                if content == "": continue
                tm = 1.0
                while True:
                    try:
                        ans = await self.persite_gpt.addMessageAsync(
                            query=f"Первоначальный вопрос:<{query}>, Тема: <{sub_theme}>, Сайт: <{site}>, Содержимое:\n\n{content[:self.site_maximum]}"
                        )
                        try:
                            json_ans = self.xml_parser(ans)
                            # with open(f"./sites_{rnd.randint(0, 1000000)}.json", "a") as f:
                            #     f.write(ans + "\n")
                        except Exception as ex:
                            await debugHandler(f"Failed to parse pseudo-HTML: {ex}")
                            with open(f"./sites_failed_{rnd.randint(0, 1000000)}.json", "a") as f:
                                f.write(ans + "\n")
                                continue
                        if json_ans["status"] == "True":
                            google_analysis[sub_theme][site] = json_ans["analysis"]
                            sources.append(site)
                        break
                    except gpt.g4f.errors.ResponseStatusError as ex:
                        print(f"[1] Error: {ex.args}")
                        time.sleep(tm)
                        tm *= 1.5
                    except Exception as ex:
                        print(f"[1] Undefinded Error: {ex}")
                        time.sleep(tm)

        # with open("./assets/analysis.json", "w") as f:
        #     try:
        #         jn.dump(google_analysis, f, indent=4, ensure_ascii=False)
        #     except:
        #         f.write(google_analysis)
        
        final_analysis = dict()

        if debug: await debugHandler("\nСборка анализов тем")
        self.fanalysis_gpt.setSystemQuery(self.finala_system_prompt)
        for sub_theme, sites in google_analysis.items():
            if debug: await debugHandler(f"\tСуб-тема: {sub_theme}")
            tm = 1.0
            while True:
                try:
                    final_analysis[sub_theme] = await self.fanalysis_gpt.addMessageAsync(
                        query=f"Первоначальный вопрос:<{query}>, Тема: <{sub_theme}>, Анализ сайтов:\n\n{sites}"
                    )
                    break
                except gpt.g4f.errors.ResponseStatusError as ex:
                    print(f"[2] Error: {ex.args}")
                    time.sleep(tm)
                    tm *= 1.5
                except Exception as ex:
                    print(f"[2] Undefinded Error: {ex}")
                    time.sleep(tm)

        per_site = f"# {theme_name.capitalize()}\n"
        for sub_theme, ans in final_analysis.items():
            per_site += f"## {sub_theme}\n\n"
            per_site += ans + "\n"
        

        if debug: await debugHandler("\nСборка ответа")

        self.conclusion_gpt.setSystemQuery(self.conclusion_system_prompt)
        final = ""
        while True:
            try:
                final = await self.conclusion_gpt.addMessageAsync(
                    query=f"Первоначальный вопрос: <{query}>, Анализы тем:\n\n{final_analysis}"
                )
                break
            except gpt.g4f.errors.ResponseStatusError as ex:
                print(f"[3] Error: {ex.args}")
                time.sleep(tm)
                tm *= 1.5
            except Exception as ex:
                print(f"[3] Undefinded Error: {ex}")
                time.sleep(tm)
        
        return final, per_site, theme_name, sources

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