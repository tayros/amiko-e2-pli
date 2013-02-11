from Components.Converter.Converter import Converter
from Components.Element import cached

class RemainingToText(Converter, object):
	DEFAULT = 0
	WITH_SECONDS = 1
	NO_SECONDS = 2
	IN_SECONDS = 3
	PROGRESS = 4
	WITH_SECONDSPROGRESS = 5
#+++>
	FOLLOW = 4
#+++<

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "WithSeconds":
			self.type = self.WITH_SECONDS
		elif type == "NoSeconds":
			self.type = self.NO_SECONDS
		elif type == "InSeconds":
			self.type = self.IN_SECONDS	
		elif type == "Progress":
			self.type = self.PROGRESS
		elif type == "WithSecondsProgress":
			self.type = self.WITH_SECONDSPROGRESS
#+++>
		elif type == "FOLLOW":
			self.type = self.FOLLOW	
#+++<
		else:
			self.type = self.DEFAULT

	@cached
	def getText(self):
		time = self.source.time
		if time is None:
			return ""

		(duration, remaining) = self.source.time

		prefix = ""
		tsecs = remaining
		if self.type == self.PROGRESS \
		 or self.type == self.WITH_SECONDSPROGRESS:
			tsecs = duration - tsecs
			if tsecs < 0:
				tsecs = -tsecs
				prefix = "-"
		elif tsecs > duration:
			tsecs = duration

		if self.type == self.NO_SECONDS:
			tsecs += 59

		seconds = tsecs % 60
		minutes = tsecs / 60 % 60
		hours = tsecs / 3600

		if self.type == self.WITH_SECONDS \
		 or self.type == self.WITH_SECONDSPROGRESS:
			return "%s%d:%02d:%02d" \
			 % (prefix, hours, minutes, seconds)
		elif self.type == self.NO_SECONDS \
		 or self.type == self.PROGRESS:
			return "%s%d:%02d" % (prefix, hours, minutes)
		elif self.type == self.IN_SECONDS:
			return prefix+str(tsecs)
#+++>
		elif self.type == self.FOLLOW:
			if remaining <= duration:
				prefix = "+"
			return "%s%d min" % (prefix, tsecs / 60)
#+++<
		elif self.type == self.DEFAULT:
			if remaining <= duration:
				prefix = "+"
			return "%s%d min" % (prefix, tsecs / 60).
		else:
			return "???"

	text = property(getText)
