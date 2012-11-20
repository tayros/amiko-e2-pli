from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from Tools import Notifications
from Components.Pixmap import Pixmap, MovingPixmap
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Label import Label
from Components.Button import Button
from Components.Console import Console
from Components.ConfigList import ConfigList
from Components.config import config, configfile, ConfigSubsection, ConfigEnableDisable, \
     getConfigListEntry, ConfigInteger, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Plugins.Plugin import PluginDescriptor
import ServiceReference
from enigma import *
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from re import compile as re_compile, search as re_search

import os

my_global_session = None

config.plugins.SparkVFD = ConfigSubsection()
config.plugins.SparkVFD.scroll = ConfigSelection(default = "once", choices = [("never"), ("once"), ("always")])
config.plugins.SparkVFD.brightness = ConfigSelection(default = "bright", choices = [("dark"), ("medium"), ("bright")])
config.plugins.SparkVFD.showClock = ConfigEnableDisable(default = True)
#config.plugins.SparkVFD.setDaylight = ConfigEnableDisable(default = False)
config.plugins.SparkVFD.timeMode = ConfigSelection(default = "24h", choices = [("12h"),("24h")])
config.plugins.SparkVFD.setLed = ConfigEnableDisable(default = False)
config.plugins.SparkVFD.setFan = ConfigEnableDisable(default = True)

class SparkVFDSetup(ConfigListScreen, Screen):
	skin = """
		<screen position="100,100" size="550,400" title="SparkVFD Setup" >
		<widget name="config" position="20,10" size="460,350" scrollbarMode="showOnDemand" />
		<ePixmap position="140,350" size="140,40" pixmap="skin_default/buttons/green.png" alphatest="on" />
		<ePixmap position="280,350" size="140,40" pixmap="skin_default/buttons/red.png" alphatest="on" />
		<widget name="key_green" position="140,350" size="140,40" font="Regular;20" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_red" position="280,350" size="140,40" font="Regular;20" backgroundColor="#9f1313" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		self.onClose.append(self.abort)

		# create elements for the menu list
		self.list = [ ]
		self.list.append(getConfigListEntry(_("Show clock"), config.plugins.SparkVFD.showClock))
		self.list.append(getConfigListEntry(_("Time mode"), config.plugins.SparkVFD.timeMode))
		self.list.append(getConfigListEntry(_("Set led"), config.plugins.SparkVFD.setLed))
		self.list.append(getConfigListEntry(_("Brightness"), config.plugins.SparkVFD.brightness))
		self.list.append(getConfigListEntry(_("Scroll long strings"), config.plugins.SparkVFD.scroll))
		self.list.append(getConfigListEntry(_("Set fan"), config.plugins.SparkVFD.setFan))
		ConfigListScreen.__init__(self, self.list)

		self.Console = Console()
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))

		# DO NOT ASK.
		self["setupActions"] = ActionMap(["SetupActions"],
		{
			"save": self.save,
			"cancel": self.cancel,
			"ok": self.save,
		}, -2)

	def abort(self):
		print "aborting"

	def save(self):
		# save all settings
		for x in self["config"].list:
			x[1].save()

		if config.plugins.SparkVFD.showClock.getValue():
			sparVfd.enableClock()
		else:
			sparVfd.disableClock()

#		if config.plugins.SparkVFD.setDaylight.getValue():
#			sparVfd.enableDaylight()
#		else:
#			sparVfd.disableDaylight()

		if config.plugins.SparkVFD.timeMode.value == "24h":
			sparVfd.enableTimeMode()
		else:
			sparVfd.disableTimeMode()

		# enable/disable fan activity
		if config.plugins.SparkVFD.setFan.getValue():
			sparVfd.enableFan()
		else:
			sparVfd.disableFan()

		# enable/disable led activity
		if config.plugins.SparkVFD.setLed.getValue():
			sparVfd.enableLed()
		else:
			sparVfd.disableLed()

	# set the brightness
		brightness = 3
		if config.plugins.SparkVFD.brightness.getValue() == "dark":
			brightness = 1
		elif config.plugins.SparkVFD.brightness.getValue() == "bright":
			brightness = 7
		evfd.getInstance().vfd_set_brightness(brightness)

		configfile.save()
		self.close()

	def cancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

class SparkVFD:
	def __init__(self, session):
		#print "SparkVFD initializing"
		global showmenuorpanel
		showmenuorpanel = False
		self.showtimer = eTimer()
		self.session = session
		self.service = None
		self.onClose = [ ]
		self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
			{
				iPlayableService.evSeekableStatusChanged: self.__evSeekableStatusChanged,
				iPlayableService.evStart: self.__evStart,
			})
		self.Console = Console()
		self.tsEnabled = False
		self.timer = eTimer()
		self.timer.callback.append(self.handleTimer)
		self.timer.start(1000, False)
		self.fanEnabled = config.plugins.SparkVFD.setFan.getValue()
		self.ledEnabled = config.plugins.SparkVFD.setLed.getValue()
		self.clockEnabled = config.plugins.SparkVFD.showClock.getValue()
		if config.plugins.SparkVFD.timeMode.value == "24h":
			self.timeModeEnabled = 1
		else:
			self.timeModeEnabled = 0
		if self.fanEnabled == False:
			self.disableFan()
		else:
			self.enableFan()
		if self.ledEnabled == False:
			self.disableLed()
		else:
			self.enableLed()

	def handleTimer(self):
		global showmenuorpanel
		try:
			from Plugins.Extensions.Aafpanel.plugin import inAAFPanel
			showPanel = inAAFPanel
		except:
			#print '[SparkVFD] Error showPanel'
			showPanel = None
		try:
			from Screens.Menu import inMenu
			showMenu = inMenu
		except:
			#print '[SparkVFD] Error showMenu'
			showMenu = None
		if showMenu or showPanel:
			self.showtimer.start(4000, True)
		self.showtimer.callback.append(self.setshowmenuorpanel)
		if not showMenu and not showPanel and showmenuorpanel is True:
			showmenuorpanel = False
			self.service = self.session.nav.getCurrentlyPlayingServiceReference()
			if not self.service is None:
				service = self.service.toCompareString()
				servicename = ServiceReference.ServiceReference(service).getServiceName().replace('\xc2\x87', '').replace('\xc2\x86', '').ljust(16)
				subservice = self.service.toString().split("::")
				if subservice[0].count(':') == 9:
					servicename =subservice[1].replace('\xc2\x87', '').replace('\xc3\x9f', 'ss').replace('\xc2\x86', '').ljust(16)
				else:
					servicename=servicename
				evfd.getInstance().vfd_write_string(servicename[0:17])

	def setshowmenuorpanel(self):
		global showmenuorpanel
		showmenuorpanel = True
		self.showtimer.stop()

	def enableClock(self):
		self.clockEnabled = True
		try:
			os.popen("/bin/fp_control -dt 1")
		except OSError:
			print "no memory"

	def disableClock(self):
		self.clockEnabled = False
		try:
			os.popen("/bin/fp_control -dt 0")
		except OSError:
			print "no memory"

	def enableTimeMode(self):
		self.timeModeEnabled = 1
		try:
			os.popen("/bin/fp_control -tm 1")
		except OSError:
			print "no memory"

	def disableTimeMode(self):
		self.timeModeEnabled = 0
		try:
			os.popen("/bin/fp_control -tm 0")
		except OSError:
			print "no memory"

	def enableLed(self):
		self.ledEnabled = True
		try:
			os.popen("/bin/fp_control -l 0 1")
		except OSError:
			print "no memory"

	def disableLed(self):
		self.ledEnabled = False
		try:
			os.popen("/bin/fp_control -l 0 0")
		except OSError:
			print "no memory"

	def enableFan(self):
		self.fanEnabled = True
		try:
			os.popen("/bin/fp_control -sf 1")
		except OSError:
			print "no memory"

	def disableFan(self):
		self.fanEnabled = False
		try:
			os.popen("/bin/fp_control -sf 0")
		except OSError:
			print "no memory"

	def regExpMatch(self, pattern, string):
		if string is None:
			return None
		try:
			return pattern.search(string).group()
		except AttributeError:
			None

	def __evStart(self):
		self.__evSeekableStatusChanged()

	def getTimeshiftState(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return False
		timeshift = service.timeshift()
		if timeshift is None:
			return False
		return True

	def __evSeekableStatusChanged(self):
		tmp = self.getTimeshiftState()
		if tmp == self.tsEnabled:
			return
		if tmp:
			print "[Timeshift enabled]"
			evfd.getInstance().vfd_set_icon(0x1A,True)
		else:
			print "[Timeshift disabled]"
			evfd.getInstance().vfd_set_icon(0x1A,False)
		self.tsEnabled = tmp
		
	def shutdown(self):
		self.abort()

	def abort(self):
		print "SparkVFD aborting"

def main(session, **kwargs):
	session.open(SparkVFDSetup)

sparVfd = None
gReason = -1
mySession = None

def controlsparVfd():
	global sparVfd
	global gReason
	global mySession

	if gReason == 0 and mySession != None and sparVfd == None:
		print "Starting SparkVFD"
		sparVfd = SparkVFD(mySession)
	elif gReason == 1 and sparVfd != None:
		print "Stopping SparkVFD"
		sparVfd = None

def autostart(reason, **kwargs):
	global sparVfd
	global gReason
	global mySession

	if kwargs.has_key("session"):
		global my_global_session
		mySession = kwargs["session"]
	else:
		gReason = reason
	controlsparVfd()

def Plugins(**kwargs):
	return [ PluginDescriptor(name="SparkVFD", description="Change VFD display settings", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
		PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart) ]
