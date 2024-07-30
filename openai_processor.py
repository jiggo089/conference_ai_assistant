import sys
from openai import OpenAI, AssistantEventHandler
import os
from dotenv import load_dotenv
import re

# Загрузка переменных окружения
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OpenAI API key not found. Please set it in the .env file.")

openai = OpenAI(api_key=api_key)
thread_id = None
assistant_id = None

class EventHandler(AssistantEventHandler):
    def __init__(self, log_func):
        super().__init__()
        self.log_func = log_func
        self.buffer = ""

    def on_text_created(self, text) -> None:
        self.log_func(f"\nassistant > {text}")

    def on_text_delta(self, delta, snapshot):
        if hasattr(delta, 'value'):
            self.buffer += delta.value
            sentences = re.split(r'(?<=[.!?]) +', self.buffer)
            for sentence in sentences[:-1]:
                self.log_func(sentence.strip())
            self.buffer = sentences[-1]

    def on_run_completed(self):
        if self.buffer:
            self.log_func(self.buffer.strip())
            self.buffer = ""

def process_audio(filename, log_func):
    global thread_id, assistant_id

    with open(filename, "rb") as audio_file:
        transcription = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    log_func(f"Transcription: {transcription.text}")
    transcription_text = transcription.text  # Извлечение текста из транскрипции

    # Убедимся, что transcription_text является строкой
    if not isinstance(transcription_text, str):
        transcription_text = str(transcription_text)

    if thread_id is None or assistant_id is None:
        # Инициализация нового потока и ассистента
        thread = openai.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": transcription_text  # Передача текста транскрипции
                }
            ]
        )
        assistant = openai.beta.assistants.create(
            name="Interview Assistant",
            description="Assistant for answering interview questions.",
            model="gpt-4-turbo"
        )
        thread_id = thread.id
        assistant_id = assistant.id
        # Сохранение идентификаторов в файл
        with open('session_ids.txt', 'w') as f:
            f.write(f"{thread_id}\n{assistant_id}\n")
    else:
        # Добавление нового сообщения в существующий поток
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=transcription_text
        )

    # Потоковая передача с использованием EventHandler
    with openai.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant_id,
        instructions="""
        ты мой ассистент по прохождению онлайн интервью на работу. отвечай на русском языке.
        давай ответы в формате top-to-down (то есть кратко вначале сообщения, и далее более подробно)
        вот мой бекграунд:
            Главный системный аналитик
            Проект NDA1 (Разработка хранилища на PostgreSQL)
            -Анализ источников данных, существующих потоков данных, и процессов обработки/преобразования данных. Сбор требований бизнеса
            -Подготовка маппинга данных систем источников с системами потребителей
            -Разработка хранилища – миграция с MS SQL Server на PostgreSQL. 
            -Формирование ODS, DDS, DM слоев хранилища DWH. 
            -Разработка документации интеграционного взаимодействия, проектных решений интеграции информационных систем (1C, Power BI, PostgreSQL)
            -Анализ текущей и разработка новой логической, физической модели данных в формате data vault 2.0
            -Формирование документации и проведение Программы и методик испытаний (ПМИ) и Приемо-сдаточных испытаний (ПСИ) проекта
            
            Проект NDA2 (Миграция на Greenplum)
            -Формирование технической, методической документации, s2t (source to target) маппинги, отчеты ПСИ
            -Формирование витрины данных DWH
            -Тестирование и приемо-сделанные испытания витрины
            -Сопровождение логической, физической модели данных с использованием SAP power designer. Архитектура по типу data vault 2.0 и 3NF.
            -Формирование бизнес глоссария (дата каталога) Alteryx Connect, описание элементов данных и
            других метаданных
            -Формирование правил системы верификации данных (контроль качества данных), инцидент
            менеджмент
            -Взаимодействие с бизнесом, заказчиком витрины, и другими стейкхолдерами проекта на всех
            этапах
            -Наставничество и онбординг младших сотрудников
            -SQL запросы для формирования витрины, оптимизация запросов и тестирование
            -использование Greenplum (Arenadata DB) на регулярной основе для задач формирования витрины и анализа источников
            - использование Oracle, Clickhouse, ms SQL - в качестве дополнительного анализа внешних, неКХД баз данных
            - использование postman на уровне запросов для анализа данных
            - базовый функционал на БД Hadoop. Apache Spark на языке scala и pyspark для задач дата инжиниринга, разработки витрин, и аналитики данных
            -работа по спринтам Scrum&Kanban, трекинг задач в Jira, ведение документации в confluencе.

        что известно о компании с кем проходит интервью:
        Косметическая компания:
            Предпроект: обследование текущих витрин и анализ того чего не хватает или того что можно доработать.
            Проект: Разработка нового хранилища данных (стек GreenPlum, ClickHouse)""",
        event_handler=EventHandler(log_func),
    ) as stream:
        stream.until_done()

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print("Usage: python openai_processor.py <filename> [<thread_id> <assistant_id>]")
        sys.exit(1)

    filename = sys.argv[1]
    if len(sys.argv) == 4:
        thread_id = sys.argv[2]
        assistant_id = sys.argv[3]

    process_audio(filename, print)
