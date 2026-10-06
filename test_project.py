import telegram
import pytest
import time
from os import environ
from os import path

from project import Spending
from project import validate_message
from project import get_one_message
from project import generate_chart

@pytest.mark.asyncio
async def test_validate_message():
    with pytest.raises(ValueError):
        await validate_message("Twenty", test=True)
        await validate_message("Twenty, Uber", test=True)
        await validate_message("Uber yesterday, comfort", test=True)
        await validate_message("Twenty", test=True)

    valid_messages = [
        "Uber, 20, yesterday",
        "Twenty on uber",
        "this morning, 20 on uber"
    ]
    for vm in valid_messages:
        assert await validate_message(vm) == vm


@pytest.mark.asyncio
async def test_get_one_message():
    bot = telegram.Bot(environ["TELEGRAM_BOT_KEY"])
    async with bot:
        if len(await bot.get_updates()) == 0:
            with pytest.raises(SystemExit):
                await get_one_message()
        else:
            assert type(await get_one_message()) == type(())
            assert len(await get_one_message()) == 3


@pytest.mark.asyncio
async def test_generate_chart():
    for i in ["1", "2", "3"]:
        initial_time = time.time()
        chart_file_name = await generate_chart(i, test=True)
        assert path.getctime(chart_file_name) > initial_time

@pytest.mark.asyncio
async def test_Spending():
    valid_dict = {
        "item": "Televisão",
        "value": "300",
        "category": "Conforto",
        "payment_method": "Crédito",
        "spending_date": "2020-01-01",
        "installments": "12"
    }

    invalid_dict = {
        "item": "",
        "value": None,
        "category": "Entretenimento",
        "payment_method": "cartão de crédito",
        "spending_date": "01-01-2020",
        "installments": "twelve"
    }

    spending = Spending(valid_dict)

    assert str(spending) == "Television cost a total value of 300.0"

    for i in invalid_dict:
        with pytest.raises(ValueError):
            setattr(spending, i, invalid_dict[i])
