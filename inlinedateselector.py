import calendar
from datetime import datetime, timezone, timedelta
from enum import Enum
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# Date string format - todo: @salonso I don't want to work with dates rn, and we have to do this conversion anyways; let's do it later if we have time
DATE_STR_FORMAT = "{Y}/{M}/{D} {h}:{m}:00"

# Auxiliary constants
CONST_MAX_MONTHS	= 12
CONST_MAX_HOURS 	= 24
CONST_MAX_MINUTES 	= 60

# Default timezone, UTC-4 (VST)
DEFAULT_TIMEZONE = timezone(-timedelta(hours=4))

def pad_zeros(number, width):
	return str(number).rjust(width, "0")

class InlineDateSelectorAction(Enum):
	ACTION_MONTH_UP 	= ("︿", "$month_up")
	ACTION_MONTH_DOWN 	= ("﹀", "$month_down")
	ACTION_DAY_UP 		= ("︿", "$day_up")
	ACTION_DAY_DOWN 	= ("﹀", "$day_down")

	ACTION_HOUR_UP		= ("︿", "$hour_up")
	ACTION_HOUR_DOWN	= ("﹀", "$hour_down")
	ACTION_MINUTE_UP	= ("︿", "$minute_up")
	ACTION_MINUTE_DOWN	= ("﹀", "$minute_down")

	ACTION_DATE_CONFIRM = ("Confirmar", "$date_confirm")
	ACTION_NO_OP 		= ("", "$noop")

	@classmethod
	def has_action(cls, action_string):
		return action_string in [member.value[1] for member in cls]

	def tag(member):
		return member.value[0]

	def action_string(member):
		return member.value[1]

class InlineDateSelectorState(Enum):
	IDLE 					= 0
	SELECTION_ACTIVE 		= 1
	SELECTION_COMPLETE		= 2	

class InlineDateSelector():
	def __init__(self):

		# Set initial state
		self.selector_state = InlineDateSelectorState.IDLE
		self.confirmed_date = None

		# Set initial date values
		today 				= datetime.now(DEFAULT_TIMEZONE)
		self.year 			= today.year
		self.month_number 	= today.month

		# Inital month list and abbr
		self.month_list		= list(calendar.month_abbr)
		self.month_abbr		= self.month_list[self.month_number]

		# Initial day and days-in-month
		self.days_in_month	= self.get_days_in_month()
		self.day 			= today.day

		# Default time
		self.time_hour		= today.hour
		self.time_minute	= today.minute

	def is_action(self, string):
		return string.startswith("$")

	def is_action_valid(self, action):
		
		# Check for no-ops
		if action == InlineDateSelectorAction.ACTION_NO_OP.action_string():
			return False

		return True

	def is_action_up(self, action):

		# Check if action is action-up
		if  action == InlineDateSelectorAction.ACTION_MONTH_UP.action_string() or \
			action == InlineDateSelectorAction.ACTION_DAY_UP.action_string() or \
			action == InlineDateSelectorAction.ACTION_HOUR_UP.action_string() or \
			action == InlineDateSelectorAction.ACTION_MINUTE_UP.action_string():

			return True

		return False

	def get_days_in_month(self):

		# Month range returns a tuple, of which the second entry is the number of days
		month_range = calendar.monthrange(self.year, self.month_number)
		return month_range[1]

	def get_inline_keyboard(self):

		# Create action-up buttons
		row_up = [
			InlineKeyboardButton(InlineDateSelectorAction.ACTION_DAY_UP.tag(), callback_data = InlineDateSelectorAction.ACTION_DAY_UP.action_string()),
			InlineKeyboardButton(InlineDateSelectorAction.ACTION_MONTH_UP.tag(), callback_data = InlineDateSelectorAction.ACTION_MONTH_UP.action_string()),
			InlineKeyboardButton(InlineDateSelectorAction.ACTION_HOUR_UP.tag(), callback_data = InlineDateSelectorAction.ACTION_HOUR_UP.action_string()),
			InlineKeyboardButton(InlineDateSelectorAction.ACTION_MINUTE_UP.tag(), callback_data = InlineDateSelectorAction.ACTION_MINUTE_UP.action_string())
		]

		# Create action-down buttons
		row_down = [
			InlineKeyboardButton(InlineDateSelectorAction.ACTION_DAY_DOWN.tag(), callback_data = InlineDateSelectorAction.ACTION_DAY_DOWN.action_string()),
			InlineKeyboardButton(InlineDateSelectorAction.ACTION_MONTH_DOWN.tag(), callback_data = InlineDateSelectorAction.ACTION_MONTH_DOWN.action_string()),
			InlineKeyboardButton(InlineDateSelectorAction.ACTION_HOUR_DOWN.tag(), callback_data = InlineDateSelectorAction.ACTION_HOUR_DOWN.action_string()),
			InlineKeyboardButton(InlineDateSelectorAction.ACTION_MINUTE_DOWN.tag(), callback_data = InlineDateSelectorAction.ACTION_MINUTE_DOWN.action_string())
		]

		# Create data fields
		row_data = [
			InlineKeyboardButton(pad_zeros(self.day, 2), callback_data = InlineDateSelectorAction.ACTION_NO_OP.action_string()),
			InlineKeyboardButton(self.month_abbr, callback_data = InlineDateSelectorAction.ACTION_NO_OP.action_string()),
			InlineKeyboardButton(pad_zeros(self.time_hour, 2), callback_data = InlineDateSelectorAction.ACTION_NO_OP.action_string()),
			InlineKeyboardButton(":" + pad_zeros(self.time_minute, 2), callback_data = InlineDateSelectorAction.ACTION_NO_OP.action_string())
		]

		row_confirm = [
			InlineKeyboardButton(InlineDateSelectorAction.ACTION_DATE_CONFIRM.tag(), callback_data = InlineDateSelectorAction.ACTION_DATE_CONFIRM.action_string())
		]

		# Build buttons
		buttons = [row_up, row_data, row_down, row_confirm]
		keyboard = InlineKeyboardMarkup(buttons)

		# Update state
		self.selector_state = InlineDateSelectorState.SELECTION_ACTIVE

		return keyboard

	def update_month(self, is_up):

		# Get delta value
		delta = 1 if is_up else -1

		# Check boundary conditions
		if self.month_number + delta > CONST_MAX_MONTHS:
			self.month_number = 1

		elif self.month_number + delta < 1:
			self.month_number = CONST_MAX_MONTHS

		# If boundary conditions are not a problem, simply update
		else:
			self.month_number += delta

		# Get new month abbreviation
		self.month_abbr = self.month_list[self.month_number]

		# Update day list and handle day changes
		self.days_in_month = self.get_days_in_month()

		# If day is beyond self.days_in_month, set it to self.days_in_month
		if self.day > self.days_in_month:
			self.day = self.days_in_month

	def update_day(self, is_up):
		
		# Get delta value
		delta = 1 if is_up else -1

		# Check boundary conditions
		if self.day + delta > self.days_in_month:
			self.day = 1

		elif self.day + delta < 1:
			self.day = self.days_in_month

		# Update as usual
		else:
			self.day += delta

	def update_hour(self, is_up):
		
		# Get delta value
		delta = 1 if is_up else -1

		# Update hour
		self.time_hour = (self.time_hour + delta) % CONST_MAX_HOURS

	def update_minute(self, is_up):
		
		# Get delta value
		delta = 1 if is_up else -1

		# Update minute
		self.time_minute = (self.time_minute + delta) % CONST_MAX_MINUTES

	def handle_confirm(self, update, context):

		# Collapse keyboard to user selection
		row_data = [
			InlineKeyboardButton(pad_zeros(self.day, 2), callback_data = InlineDateSelectorAction.ACTION_NO_OP.action_string()),
			InlineKeyboardButton(self.month_abbr, callback_data = InlineDateSelectorAction.ACTION_NO_OP.action_string()),
			InlineKeyboardButton(pad_zeros(self.time_hour, 2), callback_data = InlineDateSelectorAction.ACTION_NO_OP.action_string()),
			InlineKeyboardButton(":" + pad_zeros(self.time_minute, 2), callback_data = InlineDateSelectorAction.ACTION_NO_OP.action_string())
		]

		keyboard = InlineKeyboardMarkup([row_data])
		update.callback_query.edit_message_reply_markup(reply_markup = keyboard)

	def handle_selector_action(self, update, context, action):
		
		is_valid = self.is_action_valid(action)

		# If invalid, do nothing
		if not is_valid:
			return

		# If action is $date_confirm, return immediately
		if action == InlineDateSelectorAction.ACTION_DATE_CONFIRM.action_string():
			self.handle_confirm(update, context)
			return True

		is_action_up = self.is_action_up(action)

		# Check for month change
		if action == InlineDateSelectorAction.ACTION_MONTH_UP.action_string() or action == InlineDateSelectorAction.ACTION_MONTH_DOWN.action_string():
			self.update_month(is_action_up)

		# Check for day change
		elif action == InlineDateSelectorAction.ACTION_DAY_UP.action_string() or action == InlineDateSelectorAction.ACTION_DAY_DOWN.action_string():
			self.update_day(is_action_up)

		# Check for hour change
		elif action == InlineDateSelectorAction.ACTION_HOUR_UP.action_string() or action == InlineDateSelectorAction.ACTION_HOUR_DOWN.action_string():
			self.update_hour(is_action_up)

		elif action == InlineDateSelectorAction.ACTION_MINUTE_UP.action_string() or action == InlineDateSelectorAction.ACTION_MINUTE_DOWN.action_string():
			self.update_minute(is_action_up)

		keyboard = self.get_inline_keyboard()
		update.callback_query.edit_message_reply_markup(reply_markup = keyboard)

		return False

	def handle_callback_query(self, update, context):
		
		# Safety check
		if update.callback_query.data is not None and self.selector_state == InlineDateSelectorState.SELECTION_ACTIVE:

			# Get data
			data_string = update.callback_query.data

			# Check if is action
			if self.is_action(data_string) and InlineDateSelectorAction.has_action(data_string):
				confirmed = self.handle_selector_action(update, context, data_string)
				
				# If date was confirmed, return it immediately after collapsing keyboard in handle_confirm
				if not confirmed:
					return None
				else:
					# Set state to complete and return
					self.confirmed_date = DATE_STR_FORMAT.format(Y = self.year, M = self.month_number, D = self.day, h = self.time_hour , m = self.time_minute)
					self.selector_state = InlineDateSelectorState.SELECTION_COMPLETE

					return self.confirmed_date

	def reset(self, persist = False):

		# Reset state of selector
		self.selector_state = InlineDateSelectorState.IDLE
		self.confirmed_date = None

		# In some scenarios, we know two successive dates will be really close
		if persist: return

		# If no persist, reset date variables
		today 				= datetime.now(DEFAULT_TIMEZONE)
		self.year 			= today.year
		self.month_number 	= today.month
		self.month_abbr		= self.month_list[self.month_number]
		self.days_in_month 	= self.get_days_in_month() 
		self.day 			= today.day
		self.time_hour		= today.hour
		self.time_minute	= today.minute