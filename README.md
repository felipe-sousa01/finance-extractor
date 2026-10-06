# PERSONAL FINANCE BOT

#### Video Demo: <https://www.youtube.com/watch?v=TRu8fSyApkM>

#### Description:

**OVERVIEW**

This is a project that was born from the need of having a good finance control and the inconvenience of stopping to remember all of the expenses on a given period of time when taking them to my personal log table.

Using an LLM to convert my inputs into structured data, the automation allows the use of a Telegram bot to store all of my expenses as I text to it in the very moment the cash left my pocket. The more common the spending is, the less detailed it needs to be, because the LLM is also loaded with interpretation instructions.

Once the automation is run, it collects all the non-processed messages one by one, converts them into a json via LLM, validates the json structure and content via custom class Spending, figures out which is the payment date (as it may differ from the spending date in Credit purchases), divides it into installments, and appends them to a table in Google Sheets. The user gets back a success feedback message with the structured data that was loaded.

After the processing, the user gets prompted to choose to either end the program, or select a chart to visualize their spending profile by category. The options are: the current year as a whole (pie chart), the following month (pie chart), or the current year month by month (stack plot). The charts are built from the data that is in the Google Sheets table, so they always reflect the full history, not only the messages processed in that run. That way, one can easily see if their expenses are as expected, or if there are adjustments to make.

Moreover, via the command "charts" one can directly access the charts, without having to necessarily register a new spending.

**REQUIREMENTS**

The automation uses the following non-native Python libraries / packages (all of them can be installed running "pip install -r requirements.txt"):

- python-telegram-bot: used to handle all the interaction with the Telegram API, that is, getting new messages from user and sending back.
- matplotlib: used to plot the grouped data from the expenses table.
- numpy: used alongside matplotlib as a helper in minor applications.
- text2num: used to validate the presence of a value on user message expressed as a word rather than a number, a way to validate the input without risking passing it to the LLM and risking it to hallucinate any value. (It is installed as "text2num" but imported as "text_to_num".)
- python-dotenv: used to handle the interaction with .env, where the keys and IDs are stored.
- google-genai: used to handle the interaction with Gemini API, the chosen LLM.
- google-api-python-client and google-auth: used to read from and write to the Google Sheets table through the Google Sheets API.

This automation also requires:

- A personal Telegram bot that can be created for free following the instructions on [Telegram official tutorial](https://core.telegram.org/bots/tutorial). Each bot has an API key, that must be stored in .env file in the same path of the project.
- An API key for Google Gemini. This is a trustworthy - although at times slow - and available for free LLM. You can follow the [Google official tutorial](https://ai.google.dev/gemini-api/docs/api-key?hl=pt-br) to create yours.
- A Google Sheets table and a Google service account with access to it (see **GOOGLE SHEETS SETUP** below).
- A system_prompt.txt file is also needed. A first generalistic version of it is available, but for each personal use it may be adjusted, since it is the general guide for the LLM interpretation that includes categories it will use (must be aligned with the allowed categories on the Spending class), and more importantly the examples that help the LLM to tell apart the most common expenses one will have.
- A .env file, on the same path/folder as "project.py". It must not be versioned, and must be kept in .gitignore. The below given template is to be **strictly** followed:

**.env TEMPLATE**

Your .env file must be as follows:

```
GEMINI_API_KEY="<YOUR_GEMINI_API_KEY>"
TELEGRAM_BOT_KEY="<YOUR_BOT_API_KEY>"
GOOGLE_SHEET_ID="<YOUR_GOOGLE_SHEET_ID>"
```

**It must not be versioned, must be on .gitignore** If the keys are differently named, the code may not function. The same goes for service_account_credentials.json (see below).

**GOOGLE SHEETS SETUP**

1. Create a Google Sheets table with a tab named exactly **Gastos**. The first row must contain the headers below (the program reads the range A:I, so keep the table within these nine columns):

   `item | valor | categoria | forma de pagamento | data do gasto | data de pagamento | parcelas | mês de pagamento | ano`

   The program matches the data to the columns by the header names, so they must be written exactly as above.
2. In the [Google Cloud Console](https://console.cloud.google.com/), create a project, enable the **Google Sheets API** on it, create a **service account** and generate a **JSON key** for it.
3. Save that JSON key in the same folder as "project.py", named **service_account_credentials.json**. It must not be versioned, and must be kept in .gitignore.
4. Share the Google Sheets table with the service account e-mail (the "client_email" field in the JSON key), with **Editor** permission.
5. Copy the table ID (the part of the table URL between "/d/" and "/edit") to the GOOGLE_SHEET_ID variable in .env.
6. Set the table locale to **Brazil** and keep the "valor" column formatted as currency. The charts expect values in the Brazilian format (such as "R$ 1.234,56") and dates as dd/mm/yyyy.

You can check that the connection is working by running "python sheets_api_test.py", that just prints the headers and the rows it reads from the table.

**USE INSTRUCTIONS**

The only inputs the automation requires are the messages from Telegram. The automation does not support inputs directly from the CLI.

To run the automation, the command on the CLI is "python project.py". No arguments necessary.

When run, the code automatically searches for new messages. **If no new message is found, the program is exited**. If found, the automation loops over every message on the [Telegram update queue](https://core.telegram.org/api/updates), assuming that every one of them is a spending.

All the user needs to do is send how many messages they want to the bot and run the automation at a convenient time.

Valid spending messages examples (given the current set of examples on system_prompt.txt):

```
- "No dia 2026-04-01 paguei a conta de internet, 50 reais, crédito, 1 parcela. Custos Fixos."
- "Recarga do cartão de ônibus, 40 reais."
- "Em 2026-05-16 gastei 95 reais num restaurante japonês, paguei em dinheiro. Prazeres."
```

The allowed categories are Custos Fixos, Conforto, Prazeres, Liberdade Financeira, Metas and Conhecimento, and the allowed payment methods are Crédito, Débito and Pix/Dinheiro. If the date is not informed, today is assumed, and if the payment method is not informed, Crédito is assumed.

The user should expect to receive a confirmation message on Telegram such as the below for each of the expenses:

```
Spending successfully added:

Item: Conta de internet
Category: Custos Fixos,
Total Value: 50.0
Installments: 1
Installment Value: 50.0
Payment method: Crédito
Payment date: 2026-05-01
```

After getting the feedback message(s), the user will be prompted with:

```
Please choose:

0 End program
1 Generate spendings by category in the current year
2 Generate spendings by category for next month
3 Generate spendings by category month-by-month on the current year
```

To which they should answer with the corresponding number alone. If they fail to do so in 10 seconds, the program will be automatically exited. If they answer anything other than the showed numbers, the program will reprompt them up until three times before exiting automatically. Upon sending a valid number, the program will exit (if 0) or otherwise send the requested chart to the user.

If the user sends a message with the command "charts" alone, the automation will skip the spending register script and go directly for the chart generation, prompting the user for a chart to generate and send.

If right after "charts" the user sends another message, the first request will be ignored, since the program will give the opportunity for the user to choose a chart anyway after logging the spending(s).

However, if "charts" is found between expenses messages, it will be read as an invalid input, which will exit the program.

**INVALID INPUTS**

All inputs (except the command "charts") must have at least three words (validated by regex pattern), and at least one value (can be written as word instead of numbers). If one of these two is not satisfied, the program will be exited before getting to the LLM interpretation.

If the automation finds an invalid input, the program is exited, but not before the invalid message is removed from the queue. That way, the user might rewrite the given input and run the automation again, that will start exactly from where it left off, so that it is not needed to input all of the other expenses that were after the invalid one.

**FILES DESCRIPTION**

- project.py: this is the main code, in which the core of the automation is present, including the Spending class. It depends on the existence of system_prompt.txt, .env and service_account_credentials.json. It writes to the Google Sheets table and generates 1_year_pie.png, 2_month_pie.png and 3_year_stack.png.
- requirements.txt: set of libraries / packages required to run the automation. Does not contain all of the requirements. Check the **REQUIREMENTS** section for more details.
- system_prompt.txt: this is the file that contains the system instructions used for the LLM. It contains allowed categories, json general schema, and common examples for the categories. The user is encouraged to change/enrich the examples with the expenses that are more common to them. The user might also want to change the categories, which is possible, but should also do it on the Spending class allowed categories.
- sheets_api_test.py: small standalone script to check the connection with the Google Sheets table. Prints the headers and the rows read from the "Gastos" tab.
- 1_year_pie.png: pie chart that shows the expenses of the whole current year, grouped by category. Generated by 'project.py'.
- 2_month_pie.png: pie chart that shows the expenses of the following month, grouped by category. Generated by 'project.py'.
- 3_year_stack.png: stack plot that shows the expenses of the current year month by month, grouped by category. Generated by 'project.py'.
- test_project.py: test script that checks if the message validation is working, the proper values are being returned on get_one_message function, the charts are being generated, and the Spending class validation is rejecting invalid inputs. Run "pytest test_project.py" to test it. Since project.py connects to Telegram and Google Sheets, the tests also need the .env and service_account_credentials.json files to run.

**TESTING THE AUTOMATION**

Run "pytest test_project.py" to test it.

- test_validate_message: tests the basic validation of the input messages with both valid and invalid edge examples.
- test_get_one_message: tests if it is ending the program if there are no new messages and if it is returning all three expected values otherwise.
- test_generate_chart: test if all charts are being generated when prompted to
- test_Spending: test if the Spending valid instantiation is working and if invalid inputs are being rejected

Any change on project.py must have the tests on test_project on sight (if it is the user intent to change the program behavior, the tests might not be fit to the new behavior)

**CUSTOM METHODS AND FUNCTIONS**

- Spending instantiation: receives a dict to turn it into the validated object.
- Spending.add_month(): adds a given quantity of months to a given ISO formatted date. The output is an ISO formatted date, set always to day 1 of the resulting month. Users are encouraged to change the day accordingly to their credit card bill payment date.
- Spending.add_pay_date(): based on the spending date and payment method, defines a payment date. Users are encouraged to change the "closing_date_day" to their credit card bill closing date day.
- Spending.to_rows(): converts a Spending instance into a list of dicts, one per installment, with the same column names as the Google Sheets table.
- Spending.divide_into_installments(): divides the total values into installments of equal value, based on the installments informed on the user message.
- All the attributes to Spending objects have setters with proper validations.
- get_one_message(): tries to get the oldest message on the update queue. If there are none, exits the program.
- validate_message(): validates if the user message satisfies minimum requirements for being loaded into the LLM for translation. Exits the program if not, after taking the message out of the queue.
- convert_to_dict(): Gets the validated message as an input, loads it into the LLM, gets the response, parses it as a json and converts into a dict, which is the input for Spending class.
- success_feedback_message(): writes the success feedback message that is sent to the user when a spending is properly added to the Google Sheets table.
- send_message(): sends a given message to a specific chat_id on Telegram. Just for text.
- ask_user_for_chart(): prompts the user on Telegram to choose a chart to generate or exit the program. Handles AFK users (max 10 seconds to choose) and a maximum of 3 tries until a valid response.
- generate_pie(): reads the Google Sheets table, then generates and saves a pie chart with expenses by category. If given a month, filters the data to generate this month's pie chart, if not generates the chart for the whole 'year' that is given as a parameter.
- generate_stackplot(): reads the Google Sheets table, then generates and saves the chart for the current year's (based on the moment the program is run) month by month spending profile (by category).
- generate_chart(): routes based on user decision which chart will generated, and sends back the message with the chosen generated chart as well.

**DESIGN CHOICES**

The main design choice that was made was to whether or not use a webhook for the messages. I chose not to, mainly because, as the program won't be online at all times, it is more convenient to use the bot chat as a "storage", that will be "emptied" when the user is able to run the automation.

The expenses are stored in a Google Sheets table instead of a local file, so the table can be checked and edited from anywhere, and the charts are always built from the complete history.
