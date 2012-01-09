# Shane Tully
# 09.18.11
# Magnetic card check-in application for Penn State ACM

import os
import re
import sys
from datetime import datetime

import Constants as c

# The MySQLdb module must be available
try:
   import MySQLdb
except ImportError:
   print "This script requires the MySQLdb module to be installed. Exiting."
   sys.exit(1) 


class DB:
   def __init__(self, dbHost, dbTable, dbUser, dbPass):
      self.dbHost = dbHost
      self.dbTable = dbTable
      self.dbUser = dbUser
      self.dbPass = dbPass

   def connect(self):
      # If a password was not given, ask for it
      if self.dbPass == "":
         self.dbPass = getDbPass()

      try:
         # Connect to the database server
         self.dbConn = MySQLdb.connect(host=self.dbHost, user=self.dbUser, passwd=self.dbPass, db=self.dbTable)
         return c.SUCCESS
      except MySQLdb.Error, e:
         # Bad password error
         if "Access denied" in e.args[1]:
            return c.BAD_PASSWD
         # Other error
         else:
            return c.FAILURE


   def close(self):
      self.dbConn.close()


   def addCard(self, cardID, accessID, initialPoints):
      # Init some stuff that could cause problems if not initialized
      sqlError = None

      # Get a cursor to the DB
      cursor = self.dbConn.cursor()
      
      try:
         # Add the new record into the DB
         cursor.execute("""INSERT INTO points (cardID, accessID, points) values (\'%s\', \'%s\', %s);""" % (cardID, accessID, initialPoints))
         status = c.SUCCESS
      except MySQLdb.Error, e:
         status = c.SQL_ERROR
         sqlError = e
      finally:
         cursor.close()

      return {"addCardStatus": status, "accessID": accessID, "cardID": cardID, "sqlError": sqlError}


   def checkin(self, cardID, pointValue):
      # Init some stuff that could cause problems if not initialized
      accessID = None
      sqlError = None

      # Get a cursor to the DB
      cursor = self.dbConn.cursor()

      try:
         # Get the last check-in time
         cursor.execute("""SELECT last_checkin FROM points WHERE cardID=\'%s\';""" % (cardID))

         # Ensure that the card is in the database
         if cursor.rowcount == 0:
            status = c.CARD_NOT_IN_DB
            # Raise a generic exception to break out of the try block
            raise Exception
         else:
            result = cursor.fetchone()

         # Verify the check-in times
         if c.ALLOW_CHECKIN_WITHIN_HOUR:
            status = c.SUCCESS
         else:
            status = self.checkCheckinTime(result[0])


         if status == c.SUCCESS:
            # Update the database with the new points         
            cursor.execute("""UPDATE points SET points=points+%s WHERE cardID=\'%s\';""" % (pointValue, cardID))

            # Grab the access ID that just checked-in to print confirmation
            cursor.execute("""SELECT accessID FROM points WHERE cardID=\'%s\';""" % (cardID))

            accessID = cursor.fetchone()[0]
      except MySQLdb.Error, e:
         status = c.SQL_ERROR
         sqlError = e
      except Exception, e:
         pass
      finally:
         cursor.close()

      return {"checkinStatus": status, "accessID": accessID, "cardID": cardID, "sqlError": sqlError}

   
   def checkCheckinTime(self, lastCheckin):
      # Get the current date/time
      curDate = datetime.now()

      # The last_checkin column was added after the DB was initially populated meaning it could be a NoneType
      # Only check the dates if this is not the case
      if lastCheckin and datetime.date(curDate) == datetime.date(lastCheckin):
         tmzAdjust = 0
         
         # Check that the current system time is at least one hour greater than the last check-in time
         if (datetime.time(curDate).hour+tmzAdjust == datetime.time(lastCheckin).hour or
             (datetime.time(curDate).hour+tmzAdjust == datetime.time(lastCheckin).hour+1 and
              datetime.time(curDate).minute < datetime.time(lastCheckin).minute)):
            return c.BAD_CHECKIN_TIME
         # If the current system time is before the check-in time, do not allow check-in
         elif datetime.time(curDate).hour+tmzAdjust < datetime.time(lastCheckin).hour:
            return c.FUTURE_CHECKIN_TIME
      # If the current system date is before the check-in date, do not allow check-in
      elif lastCheckin and datetime.date(curDate) < datetime.date(lastCheckin):
         return c.FUTURE_CHECKIN_TIME
      else:
         return c.SUCCESS


   def showPoints(self, accessID=""):
      # Init result and sqlError
      result = None
      sqlError = None

      # Get a cursor to the DB
      cursor = self.dbConn.cursor()

      try:
         # Either get all access ID's and points from DB or just one access ID
         if accessID == "":
            cursor.execute("""SELECT accessID, points FROM points ORDER BY points DESC;""")
         else:
            cursor.execute("""SELECT points FROM points WHERE accessID=\'%s\';""" % (accessID))

         # Show error if no results (access ID is not in database)
         if cursor.rowcount == 0:
            status = c.NO_RESULTS
         else:
            result = cursor.fetchall()
            status = c.SUCCESS

      except MySQLdb.Error, e:
            status = c.SQL_ERROR
            sqlError = e
      finally:
         cursor.close()

      return {"showPointsStatus": status, "pointsTuple": result, "sqlError": sqlError}