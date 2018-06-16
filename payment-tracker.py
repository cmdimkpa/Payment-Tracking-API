"""
Title: Payment Tracking API project
Ver: 1.0.0
Author: Monty Dimkpa
License: Use freely but say hi! - cmdimkpa@gmail.com
"""

# API core tools

from block_magic.blockmagic_client import *
from flask import Flask, Response
import json, datetime

# Cryptography tools (for API keys)

import hashlib
from random import random

global crypto_gen, potential

crypto_gen = hashlib.md5(); potential = 1000000000000;

# initialize the Flask app
app = Flask(__name__)

# Data Manager initial tasks: create data blocks on the blockchain
CreateBlock("APIKeyStore")
CreateBlock("PaymentDataStore")

# Useful functions

def SendResponse(message,code):
	# send a HTTP message
	return Response(json.dumps(message), status=code, mimetype='application/json')

def new_api_key():
	# generate an API key
	crypto_gen.update(str(int(random()*potential)))
	return crypto_gen.hexdigest()

def timestamp():
	# timestamp a transaction
	date = datetime.datetime.today()
	return {"day":date.day,"month":date.month,"year":date.year}

def create_account():
	# make new API key
	api_key = new_api_key()
	# send API key to APIKeyStore
	SendData("APIKeyStore",[{"keys":api_key}])
	# return success message
	return {'info':'Account created successfully.','api_key':api_key},200

def date_to_number(date):
	# convert a date to a number
	mm,dd,yyyy = map(int,date)
	return (yyyy*100 + mm)*100+dd

def to_text_date(date):
	# convert a list form of date to mm/dd/yyyy
	mm,dd,yyyy = date
	return str(mm)+"/"+str(dd)+"/"+str(yyyy)

def payment_summary(api_key,payer,payee,from_date,to_date):
	# generate customizable payment summaries
	date_number_from = date_to_number(from_date)
	date_number_to = date_to_number(to_date)

	if date_number_to > date_number_from:
		max_date_number, min_date_number = date_number_to,date_number_from
	else:
		min_date_number, max_date_number = date_number_to,date_number_from

	payer,payee = map(lambda x:x.lower(),[payer,payee])
	# download payment info as transactions
	transactions = return_one_tx("PaymentDataStore")
	# pull matching records
	if bool(payee == "*" and payer != "*"):
		matching_records = [tx for tx in transactions if bool(tx["key"]==api_key and tx["from"]==payer and bool(date_to_number([tx["month"],tx["day"],tx["year"]])>=min_date_number and date_to_number([tx["month"],tx["day"],tx["year"]])<=max_date_number))]
		address = "to"
	elif bool(payer == "*" and payee != "*"):
		matching_records = [tx for tx in transactions if bool(tx["key"]==api_key and tx["to"]==payee and bool(date_to_number([tx["month"],tx["day"],tx["year"]])>=min_date_number and date_to_number([tx["month"],tx["day"],tx["year"]])<=max_date_number))]
		address = "from"
	elif bool(payer=="*" and payee=="*"):
		matching_records = [tx for tx in transactions if bool(tx["key"]==api_key and bool(date_to_number([tx["month"],tx["day"],tx["year"]])>=min_date_number and date_to_number([tx["month"],tx["day"],tx["year"]])<=max_date_number))]
		address = "any"
	else:
		matching_records = [tx for tx in transactions if bool(tx["key"]==api_key and tx["from"]==payer and tx["to"]==payee and bool(date_to_number([tx["month"],tx["day"],tx["year"]])>=min_date_number and date_to_number([tx["month"],tx["day"],tx["year"]])<=max_date_number))]
		address = "fixed"

	# compute summary

	if address == "any":
		summary = {"total":0,"events":[]}
		for tx in matching_records:
			summary["total"]+=float(tx["amount"])
			summary["events"].append({"to":tx["to"],"from":tx["from"],"amount":tx["amount"],"date":to_text_date([tx["month"],tx["day"],tx["year"]])})
		return summary

	elif address in ["fixed","to"]:
		summary = {"total":0,"to":{},"from":payer}
		for tx in matching_records:
			to_ = tx["to"]
			amt = float(tx["amount"])
			summary["total"]+=amt
			if to_ not in summary["to"]:
				summary["to"][to_] = {"amount":amt}
			else:
				summary["to"][to_]["amount"]+=amt
		return summary

	else:
		summary = {"total":0,"from":{},"to":payee}
		for tx in matching_records:
			from_ = tx["from"]
			amt = float(tx["amount"])
			summary["total"]+=amt
			if from_ not in summary["from"]:
				summary["from"][from_] = {"amount":amt}
			else:
				summary["from"][from_]["amount"]+=amt
		return summary

# API endpoints:

#create an account
@app.route("/payment-tracker/create-account/")
def api_create_account():
	message,code = create_account()
	return SendResponse(message,code)

#push receipts
@app.route("/payment-tracker/push-receipt/<path:receipt>")
def api_push_receipt(receipt):
	try:
		receipt = json.loads(receipt)
		# test json and proceed
		approved_pay_fields = ["from","to","amount","key"]
		error_fields = [field for field in receipt if field.lower() not in approved_pay_fields]
		if error_fields == [] and len(receipt) == len(approved_pay_fields):
			# check API key
			api_keys = return_one_lx("APIKeyStore")["keys"]
			if receipt["key"] not in api_keys:
				return SendResponse("error: your API key was not recognized",401)
			else:
				# add timestamp
				stamp = timestamp()
				for key in stamp:
					receipt[key] = stamp[key]
				# send receipt to PaymentDataStore
				SendData("PaymentDataStore",[receipt])
				return SendResponse("transaction successful.",200)
		else:
			return SendResponse("error: unrecognized pay fields. Send only 'key','to','from' and 'amount'",400)
	except:
		return SendResponse("error: check your data and try again",400)

# fetch payment summary
@app.route("/payment-tracker/payment-summary/<path:query>")
def fetch_payment_summary(query):
	try:
		query = json.loads(query)
		# test json and proceed
		approved_query_fields = ["key","payer","payee","from_date","to_date"]
		error_fields = [field for field in query if field.lower() not in approved_query_fields]
		if error_fields == [] and len(query) == len(approved_query_fields):
			# check API key
			api_keys = return_one_lx("APIKeyStore")["keys"]
			if query["key"] not in api_keys:
				return SendResponse("error: your API key was not recognized",401)
			else:
				# verify submitted parameters
				transactions = return_one_lx("PaymentDataStore")
				all_payers = transactions["from"]
				all_payees = transactions["to"]
				all_payers.append("*")
				all_payees.append("*")
				try:
					from_date = map(int,query["from_date"].split("/"))
					to_date = map(int,query["to_date"].split("/"))
					error_summary = []
					if query["payer"] not in all_payers:
						error_summary.append("payer not found")
					if query["payee"] not in all_payees:
						error_summary.append("payee not found")
					if error_summary != []:
						return SendResponse({"error(s)":error_summary},400)
					else:
						return SendResponse(payment_summary(query["key"],query["payer"],query["payee"],from_date,to_date),200)
				except:
					return SendResponse("error: check your dates - use mm/dd/yyyy format",400)
		else:
			return SendResponse("error: unrecognized query fields. Send only 'key','payer','payee','from_date (in mm/dd/yyyy)' and 'to_date (in mm/dd/yyyy)'",400)
	except:
		return SendResponse("error: check your data and try again",400)

# start web app
if __name__ == "__main__":
    app.run()
