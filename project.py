import re
import csv
import json
import asyncio
import telegram
import sys
import datetime as dt
import matplotlib.pyplot as plt
import numpy as np
from text_to_num import alpha2digit
from dotenv import load_dotenv
from google import genai
from os import environ

load_dotenv()

class Spending:
    categories = ["Fixed Expenses", "Comfort", "Fun", "Financial Freedom", "Goals", "Knowledge"]

    def __init__(self, spending_dict):
        self.item = spending_dict["item"]
        self.value = spending_dict["value"]
        self.category = spending_dict["category"]
        self.payment_method = spending_dict["payment_method"]
        self.spending_date = spending_dict["spending_date"]
        self.installments = spending_dict["installments"]

    def __str__(self):
        return f"{self.item} cost a total value of {self.value}"

    @classmethod
    def add_month(cls, iso_date, months=1):
        month = int(iso_date.split("-")[1])
        year = int(iso_date.split("-")[0])

        if month + months <= 12:
            new_iso_date = str(year) + "-" + str(month+months).zfill(2) + "-" + "01"
        else:
            years_to_add = (month+months)//12

            new_year = str(year+years_to_add)
            new_month = str((month+months)%12).zfill(2)
            new_day = "01"

            new_iso_date = new_year + "-" + new_month + "-" + new_day

        return new_iso_date

    def add_pay_date(self):
        sp_date = self.spending_date
        sp_day_int = int(sp_date.split("-")[2])

        if sp_date.split("-")[1] == "02":
            closing_date_day = 28
        else:
            closing_date_day = 29

        if self.payment_method == "Credit" and sp_day_int < closing_date_day:
            self.pay_date = self.add_month(sp_date)
        elif self.payment_method == "Credit" and sp_day_int >= closing_date_day:
            self.pay_date = self.add_month(sp_date,months=2)
        else:
            self.pay_date = sp_date

    def to_rows(self):
        return self.divide_into_installments(self.installments)

    def divide_into_installments(self, n):
        all_rows = []
        for i in range(n):
            row = {
                "item" : f"{self.item} ({i+1}/{n})",
                "value": round(self.value / n, 2),
                "category": self.category,
                "payment_method": self.payment_method,
                "spending_date": self.spending_date,
                "pay_date": self.add_month(self.pay_date, i),
                "installments": self.installments
            }

            all_rows.append(row)

        return all_rows

    @property
    def item(self):
        return self._item

    @item.setter
    def item(self, item):
        if item == "" or item is None:
            raise ValueError("Item is empty")
        self._item = item.capitalize()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if value == "" or value is None:
            raise ValueError("Value is empty")
        value = float(value)

        self._value = value

    @property
    def category(self):
        return self._category

    @category.setter
    def category(self, category):
        if category not in Spending.categories:
            raise ValueError(f"{category} is an invalid Category")

        self._category = category

    @property
    def payment_method(self):
        return self._payment_method

    @payment_method.setter
    def payment_method(self, payment_method):
        if payment_method not in ["Credit", "Money", "Debit"]:
            raise ValueError(f"{payment_method} is an invalid payment method")

        self._payment_method = payment_method

    @property
    def spending_date(self):
        return self._spending_date

    @spending_date.setter
    def spending_date(self, spending_date):
        dt.date.fromisoformat(spending_date)

        self._spending_date = spending_date

    @property
    def installments(self):
        return self._installments

    @installments.setter
    def installments(self, installments):
        if installments == "" or installments is None:
            raise ValueError("Installments is empty")
        installments = int(installments)

        self._installments = installments

    @property
    def pay_date(self):
        return self._pay_date

    @pay_date.setter
    def pay_date(self, pay_date):
        dt.date.fromisoformat(pay_date)

        self._pay_date = pay_date



async def main():
    bot = telegram.Bot(environ["TELEGRAM_BOT_KEY"])
    async with bot:
        new_messages_qty = len(await bot.get_updates())

    if new_messages_qty == 0:
        sys.exit("No new messages")

    first_message, update_id, chat_id = await get_one_message()
    if first_message.strip() == "charts" and new_messages_qty==1:
        async with bot:
            await bot.get_updates(update_id+1)
        print("Skipping to charts")
    else:
        # Case if user ask for chart and inputs spendgins after, ignore charts ask until all the inputs are processed
        if first_message.strip() == "charts":
            async with bot:
                await bot.get_updates(update_id+1)
            new_messages_qty-=1

        # Loop over spendings messages
        for _ in range(new_messages_qty):
            # Get the oldest message and validate minimum content
            message, update_id, chat_id = await get_one_message()
            plain_text = await validate_message(message, update_id, chat_id)

            # Convert plain_text in structured Object
            spending = Spending(convert_to_dict(plain_text))

            # Take the message out of the queue of updates on Telegram
            async with bot:
                await bot.get_updates(update_id+1)

            # Add pay date
            spending.add_pay_date()

            # Convert spending into actual rows for csv
            rows_to_add = spending.to_rows()

            # Add rows to table
            with open("spendings.csv", newline="", mode="a") as f:
                fieldnames = ["item","value","category","payment_method","spending_date","pay_date","installments"]
                writer = csv.DictWriter(f, fieldnames = fieldnames)
                writer.writerows(rows_to_add)

            # Send feedback message
            await send_message(success_feedback_message(spending), chat_id)

    # else:
    #     sys.exit("No new messages")

    # Check if queue is over
    async with bot:
        print ("length after loop", len(await bot.get_updates(update_id+1)))
        if len(await bot.get_updates(update_id+1)) != 0:
            sys.exit("Queue is not empty, exiting program")

    # Get user decision (generate chart or not)
    user_decision = await ask_user_for_chart(update_id, chat_id)

    # Generate chart based on user input
    if user_decision != "0":
        await generate_chart(user_decision, chat_id)


async def get_one_message():
    # In a first moment, the message will be an input here. After the downstream dev, change to Telegram API
    bot = telegram.Bot(environ["TELEGRAM_BOT_KEY"])

    async with bot:
        try:
            message = (await bot.get_updates())[0]          # [0] is the oldest message in the update queue
        except IndexError:
            sys.exit("No new messages")
        message_text = message.message.text
        update_id = message.update_id
        chat_id = message.message.chat.id

    return message_text, update_id, chat_id

async def validate_message(m, update_id=None, c_id=None, test = False):
    bot = telegram.Bot(environ["TELEGRAM_BOT_KEY"])
    m = m.strip()
    async with bot:
        if m == "":
            if test != True:
                await send_message("ERROR: Message is empty", c_id)
                await bot.get_updates(update_id+1)
            raise ValueError("Message is empty")
        elif not re.search(r"\w+[\s:,.][\s:,.]?\w+[\s:,.][\s:,.]?\w+",m):
            if test != True:
                await send_message(f"ERROR: Message '{m}' must cointain at least 3 words", c_id)
                await bot.get_updates(update_id+1)
            raise ValueError("Message must cointain at least 3 words")
        elif not re.search(r"[0-9]", alpha2digit(m, "en")):
            if test != True:
                await send_message(f"ERROR: Spending value could not be detected in '{m}'", c_id)
                await bot.get_updates(update_id+1)
            raise ValueError("Spending value could not be detected")

    return m


def convert_to_dict(p_txt):
    client = genai.Client()

    with open("system_prompt.txt", "r") as file:
        system_instruction = file.read().replace(r"{current_date}", str(dt.date.today()))

        interaction = client.interactions.create(
            model="gemini-3.5-flash-lite",
            input=p_txt,
            system_instruction=system_instruction,
            response_format={
                "mime_type": "application/json"
            }
        )

        spending_dict = json.loads(interaction.output_text)

    return spending_dict


def success_feedback_message(spending_obj):

    feedback_message = f"""
    Spending successfully added:

    Item: {spending_obj.item}
    Category: {spending_obj.category},
    Total Value: {spending_obj.value}
    Installments: {spending_obj.installments}
    Installment Value: {round(spending_obj.value/spending_obj.installments,2)}
    Payment method: {spending_obj.payment_method}
    Payment date: {spending_obj.pay_date}
    """

    return feedback_message


async def send_message(m_text,c_id):
    bot = telegram.Bot(environ["TELEGRAM_BOT_KEY"])

    await bot.send_message(text=m_text, chat_id=c_id)


async def ask_user_for_chart(update_id, c_id):
    tries = 0
    while True:
        # Send message for user input
        await send_message(
            """
Please choose:

0   End program
1   Generate spendings by category in the current year
2   Generate spendings by category for next month
3   Generate spendings by category month-by-month on the current year""",
            c_id
        )

        bot = telegram.Bot(environ["TELEGRAM_BOT_KEY"])

        # Try to get an answer in up to 10 seconds
        for i in range(10):
            async with bot:
                await asyncio.sleep(1)
                decision_message = (await bot.get_updates(update_id+1))

                if len(decision_message) > 0:
                    decision = decision_message[0].message.text.strip()

                    # Add 1 to update_id
                    update_id += 1

                    await bot.get_updates(update_id+1)
                    break
                elif i == 6:
                    await bot.send_message(text="Program will be ended in 3 seconds", chat_id=c_id)
                elif i == 9:
                    await bot.send_message(text="Ending the program", chat_id=c_id)
                    sys.exit("Ending the program due to inactivity")

        if decision in ["0","1","2","3"]:
            break
        elif tries == 3:
            await send_message("Ending program", c_id)
            sys.exit()
        else:
            tries += 1
            await send_message("Invalid input, please choose between 0, 1, 2 or 3", c_id)

    return decision


def generate_pie(f, year, month=None):

    with open(f, newline="", mode="r") as file:
        spendings = csv.DictReader(file)
        yr_spendings = []

        for s in spendings:
            if s["pay_date"].split("-")[0] == year:
                yr_spendings.append(s)

        spendings = yr_spendings

        if month:
            nxt_month_filtered_spendings = []

            for s in spendings:
                if s["pay_date"].split("-")[1] == month:
                    nxt_month_filtered_spendings.append(s)

            spendings = nxt_month_filtered_spendings

        sum_dict = {}

        for c in Spending.categories:
            sum_dict[c] = 0

        for s in spendings:
            for c in sum_dict:
                if s["category"] == c:
                    sum_dict[c]+=float(s["value"])

    colors = plt.get_cmap("viridis")(np.linspace(0.3, 1, len(sum_dict.values())))
    plt.pie(sum_dict.values(), colors=colors, labels=sum_dict.keys(), autopct="%1.1f%%", radius=1.2)

    __months = {
            "01":"Jan",
            "02":"Feb",
            "03":"Mar",
            "04":"Apr",
            "05":"May",
            "06":"Jun",
            "07":"Jul",
            "08":"Aug",
            "09":"Sep",
            "10":"Oct",
            "11":"Nov",
            "12":"Dec"
        }

    for m in __months:
        if m == month:
            next_month = __months[m]

    if month:
        plt.title(f"Spendings by category for {next_month}", y=1.05, fontweight="bold")
        chart_file_name = "2_month_pie.png"
        plt.savefig(chart_file_name)
        return chart_file_name
    else:
        plt.title(f"Spendings by category for {year}", y=1.05, fontweight="bold")
        chart_file_name = "1_year_pie.png"
        plt.savefig("1_year_pie.png")
        return chart_file_name


def generate_stackplot(file):
    __months = {
        "01":"Jan",
        "02":"Feb",
        "03":"Mar",
        "04":"Apr",
        "05":"May",
        "06":"Jun",
        "07":"Jul",
        "08":"Aug",
        "09":"Sep",
        "10":"Oct",
        "11":"Nov",
        "12":"Dec"
    }

    current_year = str(dt.date.today()).split("-")[0]

    with open(file, newline="", mode="r") as file:
        spendings = csv.DictReader(file)

        # Filter current year spendings
        current_year_spendings = []

        for s in spendings:
            if s["pay_date"].split("-")[0] == current_year:
                current_year_spendings.append(s)

        # Assign filtered spendings to main dict
        spendings = current_year_spendings

        # Create dinamically empty dict with chart data
        spendings_by_category = {}

        for c in Spending.categories:
            spendings_by_category[c] = []

        # iterate over months, populating the lists created inside the chart data dict
        for m in __months:
            n_as_str = m
            abv = __months[m]

            # Filter month "m"
            m_spendings = []
            for s in spendings:
                if s["pay_date"].split("-")[1] == n_as_str:
                    m_spendings.append(s)

            # In each category, creates and accumulates in ms_in_c (monthly spending in category). Append on list of each category
            for c in spendings_by_category:
                ms_in_c = 0
                for ms in m_spendings:
                    if ms["category"] == c:
                        ms_in_c+=float(ms["value"])

                spendings_by_category[c].append(round(ms_in_c,2))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.stackplot(__months.values(), spendings_by_category.values(), labels=spendings_by_category.keys())
    ax.legend(fontsize="small")
    ax.set_title(f"Spendings by month and category in {current_year}", fontweight="bold", y=1.05)
    ax.set_xlabel("Month")
    ax.set_ylabel("Dollars")

    chart_file_name = "3_year_stack.png"
    plt.savefig(chart_file_name)
    return chart_file_name


async def generate_chart(request,c_id=None,test=False):
    bot = telegram.Bot(environ["TELEGRAM_BOT_KEY"])
    match request:
        case "1":
            current_year = str(dt.date.today()).split("-")[0]
            chart_file_name = generate_pie("spendings.csv", year=current_year)
            if test == False:
                async with bot:
                    await bot.send_photo(c_id, open("1_year_pie.png","r+b"), caption="Spendings by category in the current year")

        case "2": # Generate chart for following month
            target_date = Spending.add_month(str(dt.date.today()))
            chart_file_name = generate_pie("spendings.csv", year=target_date.split("-")[0], month=target_date.split("-")[1])
            if test == False:
                async with bot:
                    await bot.send_photo(c_id, open("2_month_pie.png","r+b"),caption="Spendings by category for next month")

        case "3":
            chart_file_name = generate_stackplot("spendings.csv")
            if test == False:
                async with bot:
                    await bot.send_photo(c_id, open("3_year_stack.png","r+b"),caption="Spendings by category month-by-month on the current year")

    return chart_file_name

if __name__=="__main__":
    asyncio.run(main())
