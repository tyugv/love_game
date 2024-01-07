from dialogue import Dialogue

dial = Dialogue()


def handler(event, context):
    """
    функция обрабатывающая сообщения пользователя и возвращающая ответ
    """
    response = dial.update(event)
    return response
