from alice_sdk import AliceRequest, AliceResponse
from parse_tsv import parse_alphabet, parse_dialogue
import string


def clear_text(text):
    """
    Функция для очистки текста: текст переводится в нижний регистр, знаки пунктуации удаляются
    """
    return text.lower().replace('-', ' ').translate(str.maketrans('', '', string.punctuation))


class Dialogue:
    """
    класс диалога
    """
    def __init__(self, dialogue_file="data/dialogue.tsv", alphabet_file="data/alphabet.tsv"):
        self.dialogue = parse_dialogue(dialogue_file)  # загружаем игру симулятор отношений и другие реплики
        self.alphabet = parse_alphabet(alphabet_file)  # загружаем игру азбука любви

        self.current_state = 0  # номер реплики/состояния, согласно полю id в файле dialogue.tsv
        self.new_game_state = 0  # начинаем с нулевой реплики, т.е. нулевого состояния

        self.rules_state = 1  # вызов правил открывает реплику 1
        self.help_state = 1  # вызов помощи открывает реплику 1

        self.back_state = 2222  # состояние возврата к игре

        self.current_game = -1  # номер текущей игры: 0 - симулятор отношений, 1 - азбука любви, -1 - игра не выбрана
        self.choose_relationships = 3  # реплика для выбора игры "симулятор отношений"
        self.choose_alphabet = 4  # реплика для выбора игры "азбука любви"
        self.choose_game_states = {self.choose_relationships: 0, self.choose_alphabet: 1}  # номера игр для выбора

        self.error_states = {
            0: 497,
            1: 498,
            -1: 497
        }  # реплики ошибки в зависимости от выбранной игры

        # номера реплик сервиса (вызов правил, вызов помощи, ошибка)
        self.service_states = [self.rules_state, self.help_state] + list(self.error_states.values())

        self.old_session = 339  # номер реплики если у пользователя найдена предыдущая сессия

    def restart(self):
        """
        начать сначала
        """
        self.current_state = self.new_game_state
        self.current_game = -1

    def get_response(self, current_state: int):
        """
        получить ответ бота в зависимости от переданного состояния и текущей игры
        """
        # если реплика выбора игры, тогда обновляем номер игры
        if current_state in self.choose_game_states:
            self.current_game = self.choose_game_states[current_state]

        # получаем реплику по ее номеру из файла с диалогами
        current_response = self.dialogue[current_state].copy()

        # к каждой реплике сервиса добавляем кнопку возврата к игре
        if current_state in self.service_states:
            buttons = current_response['buttons'].copy()
            buttons.append({
                'text': 'Вернуться к игре',
                'hide': True,
                'next_state': self.back_state
            })
            current_response['buttons'] = buttons
        return current_response

    def service_response(self, event):
        """
        проверяем нужна ли реплика сервиса; если нужна, то выбираем подходящую
        """
        if event["session"]["new"]:
            # если в новую сессию была передана информация о старой сессии (любое состояние кроме начала игры),
            # то предлагаем пользователю восстановить старую сессию
            if self.current_state != self.new_game_state:
                current_state = self.old_session
            else:
                current_state = self.new_game_state

        # обнаружен интент "начать заново" - перезапускаем игру
        elif "START_AGAIN" in event["request"]["nlu"]["intents"]:
            self.restart()
            current_state = self.new_game_state

        # обнаружен интент "помощь" - возвращаем реплику помощи
        elif "YANDEX.HELP" in event["request"]["nlu"]["intents"]:
            current_state = self.help_state

        # обнаружен интент "правила" - возвращаем реплику правил
        elif "RULES" in event["request"]["nlu"]["intents"]:
            current_state = self.rules_state

        # возврат к игре по кнопке или текстовой команде
        elif (("command" in event["request"]) and ((clear_text(event["request"]["command"]) == "вернуться к игре") or
                                                   (clear_text(event["request"]["command"]) == "продолжить игру"))) or \
                (("payload" in event["request"]) and (int(event["request"]["payload"]) == self.back_state)):
            current_state = self.current_state

        # если не нужно возвращать реплику сервиса
        else:
            return None
        return self.get_response(current_state)

    def relationships_response(self, event):
        """
        выбор реплики/состояния для игры "Симулятор отношений"
        """
        # ошибка, если ответ пользователя не будет распознан
        current_state = self.error_states[0]

        # состояние переданное нажатием на кнопку
        if "payload" in event["request"]:
            current_state = int(event["request"]["payload"])

        # если ответ был текстовым, то сравниваем введенный текст с текстом на кнопках и переходим на состояние,
        # переданное соответствующей кнопкой
        elif "command" in event["request"]:
            for button in self.dialogue[self.current_state]["buttons"]:
                if clear_text(button["text"]) == clear_text(event["request"]["command"]):
                    current_state = button["next_state"]
                    break

        # если переданное состояние это реплика в файле диалогов и оно не сервисное (не ошибка и тд), то обновляем его
        if current_state in self.dialogue:
            if current_state not in self.service_states:
                self.current_state = int(current_state)
        return self.get_response(current_state)

    def alphabet_response(self, event):
        """
        ответы для игры "Азбука любви"
        """
        # если был распознан интент, то ищем в нем интент буквы для игры "Азбука любви"
        if len(event["request"]["nlu"]["intents"]) > 0:
            for intent in list(event["request"]["nlu"]["intents"].keys()):
                if intent in self.alphabet:
                    return self.alphabet[intent]
        return None

    def update_session_state(self, event):
        """
        получаем из сообщения пользователя актуальный номер игры и актуальный номер реплики для текущей сессии
        """
        for session_type in ["user", "session"]:
            if session_type in event["state"]:
                if "current_state" in event["state"][session_type]:
                    self.current_state = event["state"][session_type]["current_state"]
                if "current_game" in event["state"][session_type]:
                    self.current_game = event["state"][session_type]["current_game"]
                break

    def choose_response(self, event):
        """
        выбираем реплику ответа с учетом сохраненных состояний, номера игры и запроса пользователя
        """
        # проверка на вызов сервисной реплики
        service_response = self.service_response(event)
        # если была найдена сервисная реплика для запроса пользователя, то возвращаем ее
        if service_response is not None:
            current_response = service_response

        # если игра не выбрана, то проверим ответ пользователя на выбор игры, если выбора игры нет - выведем ошибку
        elif self.current_game == -1:
            current_state = self.error_states[self.current_game]
            if "payload" in event["request"]:
                current_state = int(event["request"]["payload"])
                self.current_state = current_state
            elif "command" in event["request"]:
                if clear_text(event["request"]["command"]) == "симулятор отношений":
                    current_state = self.choose_relationships
                    self.current_state = current_state
                elif clear_text(event["request"]["command"]) == "азбука любви":
                    current_state = self.choose_alphabet
                    self.current_state = current_state
            current_response = self.get_response(current_state)

        # если игра выбрана, то вызовем следующую реплику для выбранной игры
        elif self.current_game == 0:
            current_response = self.relationships_response(event)
        elif self.current_game == 1:
            current_response = self.alphabet_response(event)

        # если сообщение пользователя не подошло ни под одно условие, то реплика для ответа не найдена
        else:
            current_response = None

        # если реплика для ответа не найдена, то выводим ошибку
        if current_response is None:
            current_response = self.get_response(self.error_states[self.current_game])

        return current_response

    def update(self, event):
        # обновляем актуальную информацию об игре
        self.update_session_state(event)
        # выбираем реплику ответа
        current_response = self.choose_response(event)

        # переводим ответ в формат для Алисы
        alice_request = AliceRequest(event)
        alice_response = AliceResponse(alice_request)

        # добавляем кнопки
        if len(current_response['buttons']) > 0:
            alice_response.set_buttons([{
                'title': button['text'],
                'payload': button['next_state'],
                'hide': button['hide']
            } for button in current_response['buttons']])

        # добавляем изображение
        if current_response['image'] != '':
            alice_response.set_image({
                "image_id": current_response['image'],
                "type": "BigImage",
                # добавляем текст в описание изображения
                "description": current_response['text']})
            alice_response.set_text('')

        # если нет изображения, добавляем обычный текст
        else:
            alice_response.set_text(current_response['text'])

        # добавляем звук и озвучку текста
        # заменяем скобки в тексте на точки чтобы диктор выделял интонационно скобки как конец предложения
        # Пример: "Привет)" заменится на "Привет."

        if current_response['sound'] != '':
            alice_response.set_audio(current_response['sound'] +
                                     current_response['text'].replace(')', '.').replace('(', '.'))
        else:
            alice_response.set_audio(current_response['text'].replace(')', '.').replace('(', '.'))

        # передаем актуальный номер игры и актуальный номер реплики текущей сессии
        alice_response.set_state(self.current_state, self.current_game)

        # возвращаем ответ
        return alice_response.get_response()
