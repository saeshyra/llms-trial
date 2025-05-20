## Installation and first run
Pycharm recommended, but any IDE will work. Instructions refer to Ubuntu on WSL 2 setup. The steps might vary slightly on different configurations.

1. Install the requirements from the ``requirements.txt`` file.
2. Install mysql:
    ```console
    user@device:~$ sudo apt update && sudo apt upgrade
    user@device:~$ sudo apt install mysql-server
    user@device:~$ sudo /etc/init.d/mysql start
    user@device:~$ sudo mysql_secure_installation
    ```
3. By default the code in ``main.py`` will create and access a mysql database with some default credentials. These are in clear in the ``main.py`` file for now as it's more convenience. You can either change the password in the code according to your mysql setup, or change your USER password accordingly:
    ```console
    user@device:~$ sudo mysql
    ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$THE_PASSWORD_IN_main.py';
    ```
4. Install docker. You need the Ubuntu version of docker-compose, without the Desktop GUI. Do as follows:
    ```console
    user@device:~$ curl -fsSL https://get.docker.com -o get-docker.sh
    user@device:~$ sudo sh get-docker.sh
    user@device:~$ sudo usermod -aG docker $USER
    ```
5. Apply the necessary modification to RASA and Telegram APIs. The procedure is explained in the ``API_edits`` file.
6. Start the chatbot from the ``main.py`` file. The terminal will prompt if you want to train the RASA model or not. Do it if you don't have any previously-trained model, and also in case you change any of the interaction rules/stories. Refer to RASA docs for more info.

## Setting up the master account
The chatbot interfaces with the MyFitnessPal app. On starting the ``main.py`` file you will be asked to "setup the master account". Reply 'y' and a browser page will be opened asking you to log in into MyFitnessPal. You must use the following credentials:
- username: philhdietbotmaster
- password: Dpecmiejf2931313****

## Signing up as a user
The master account merely serves the purpose of scraping other people's accounts. The only requirement is that the master account must have this people as friends. At the moment this must be done manually.

## Using the chatbot
The chatbot supports two kinds of insights: basic (quick glance at values) and advanced (charts + text). Queries make use of entities (calories, carbs, sodium, fat, protein; all if not specified) and timeframes (today, yesterday, this week, last month, feb 20 2024, feb 20 (assumes current year), feb 20-23 etc.)

Examples of a basic query:
"How was my diet today?" -> returns calories and all macros for today
"Check my calories yesterday" -> returns calories only
"Update me on calories, fat and sugar" -> returns calories, fat and sugar

Once you have a basic insight you can ask for advanced ones with queries like "tell me more" or "more info". Again, you can specify entities(e.g. "tell me more about calories"). Once you do this you'll be presented with a button interface, offering you 3 advanced insights: intake, consistency and food analysis.
1. Intake: returns your data for the specified period as a time series with a chart and explains how you're eating on average. The chart also shows two tolerance bars (e.g. if you're eating too much or too little but within 10% tolerance this won't be considered a significant problem). Finally, you'll be informed about your "toughest day", the day in which you were the furthest from your goal
2. Consistency: A simple linear regression that uses your data points to calculate your eating trend (e.g. are you generally eating more or less during this time?). You will also be informed about your "consistency" (if you vary a lot in the amount of food you eat between days).
3. Food: a donut chart showing you the top 6 foods that gave you calories (or any other macro) in the selected time.

You can also trigger advanced insights directly, some examples:
- Check my calorie intake this week -> returns intake analysis for calories
- What food gave me the most sodium yesterday? -> returns food analysis for sodium
- Analyse my food -> returns food analysis for calories and all macros
- Am I being consistent with my fat intake? -> returns consistency analysis for sodium

N.B.: if you trigger advanced insights with a query directly and specify multiple entities (or none of them, in which case the bot will assume you want to know all of them), then the bot will show the advanced insights for calories first, then ask you (through buttons) if you want to keep going.

## Known bugs
1. Sometimes the chatbot will return an empty diary for non-empty days. This usually fixes itself by just waiting a couple of seconds and re-trying. As far as I can see this is not a code issue, it's on the MFP API.
