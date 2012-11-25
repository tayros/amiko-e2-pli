installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = CutListEditor PicturePlayer MediaScanner MediaPlayer GraphMultiEPG SocketMMI ModemSettings

if ENABLE_SPARK
SUBDIRS += SparkVFD
endif

if ENABLE_SPARK7162
SUBDIRS += SparkVFD
endif

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

install_PYTHON =	\
	__init__.py
