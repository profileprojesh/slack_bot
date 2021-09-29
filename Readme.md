# Installation
```
# venv
python -m venv .venv

# package
pip install -r requirements.txt
```

# Feature
Events till now:
* `hello` :- Message that will ask for general question
* `/out`:- Command to work with recording absent data. Commands available:
    * `/out` - > Give modal to register absent details
    * `/out -d n` where n is *number of day* ->  Record details *n* day from today, reason will be *null*
    * `/out -d n "I am travelling"`-> Record details *n* day from today, reason for *leave*
* `/out-today`:- Gets all name of member who are absent today.
* `/out-month`:- Gets all member who are absent by month.
    * `/out-month` - > All members absent in current month
    * `/out-month -m n` where n is *number of month* -> All members absent by specific month
    * `/out-month -m n false`-> All members absent by specific month, _false_ represent include weekends or not

