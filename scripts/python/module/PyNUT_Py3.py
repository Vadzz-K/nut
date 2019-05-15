#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#   
#   2018-10: Vadzz: PyNUT_Py3.py is a Python 3 abstraction class to access NUT server(s). 
#   You can use it in Python 3 programs to access NUT's upsd data server in a simple way, 
#   without having to know the NUT protocol. To import it on Python programs you have 
#   to use the following (case sensitive) : 'import PyNUT_Py3'

#   This module provides a 'PyNUTClient' class that can be used to connect and get data from an upsd data server.

import telnetlib

class PyNUTError( Exception ) :
    """ Base class for custom exceptions """
        

class PyNUTClient :
    """ Abstraction class to access NUT (Network UPS Tools) server """

    __debug       = None   # Set class to debug mode (prints everything useful for debuging...)
    __host        = None
    __port        = None
    __login       = None
    __password    = None
    __timeout     = None
    __srv_handler = None

    __version     = "3.0.0"
    __release     = "2018-05-04"


    def __init__( self, host="127.0.0.1", port=3493, login=None, password=None, debug=False, timeout=5 ) :
        """ Class initialization method
host     : Host to connect (default to localhost)
port     : Port where NUT listens for connections (default to 3493)
login    : Login used to connect to NUT server (default to None for no authentication)
password : Password used when using authentication (default to None)
debug    : Boolean, put class in debug mode (prints everything on console, default to False)
timeout  : Timeout used to wait for network response
        """
        self.__debug = debug

        if self.__debug :
            print( "[DEBUG] Class initialization..." )
            print( "[DEBUG]  -> Host  = %s (port %s)" % ( host, port ) )
            print( "[DEBUG]  -> Login = '%s' / '%s'" % ( login, password ) )

        self.__host     = host
        self.__port     = port
        self.__login    = login
        self.__password = password
        self.__timeout  = 5

        self.__connect()

    # Try to disconnect cleanly when class is deleted ;)
    def __del__( self ) :
        """ Class destructor method """
        try :
            self.__srv_handler.write( "LOGOUT\n" )
        except :
            pass

    def __connect( self ) :
        """ Connects to the defined server
If login/pass was specified, the class tries to authenticate. An error is raised
if something goes wrong.
        """
        if self.__debug :
            print( "[DEBUG] Connecting to host" )

        self.__srv_handler = telnetlib.Telnet( self.__host, self.__port )

        if self.__login != None :
            self.__srv_handler.write( ( b"USERNAME " + self.__login.encode('ascii')+b"\n" ) )
            result = self.__srv_handler.read_until( b"\n", self.__timeout ).decode('ascii')
            if result[:2] != "OK" :
                raise PyNUTError( result.replace( "\n", "") )

        if self.__password != None :
            self.__srv_handler.write( ( "PASSWORD %s\n" % self.__password ).encode('ascii') )
            result = self.__srv_handler.read_until( b"\n", self.__timeout ).decode('ascii')
            if result[:2] != "OK" :
                raise PyNUTError( result.replace( "\n", "" ) )

    def GetUPSList( self ) :
        """ Returns the list of available UPS from the NUT server
The result is a dictionary containing 'key->val' pairs of 'UPSName' and 'UPS Description'
        """
        if self.__debug :
            print( "[DEBUG] GetUPSList from server" )

        self.__srv_handler.write( b"LIST UPS\n" )
        result = self.__srv_handler.read_until( b"\n" ).decode('ascii')
        if (result != "BEGIN LIST UPS\n" ):
            raise PyNUTError( result.replace( "\n", "" ) )

        result = (self.__srv_handler.read_until( b"END LIST UPS\n" )).decode('ascii')
        ups_list = {}

        for line in result.split( "\n" ) :
            if line[:3] == "UPS" :
                ups, desc = line[4:-1].split( '"' )
                ups_list[ ups.replace( " ", "" ) ] = desc

        return( ups_list )

    def GetUPSVars( self, ups="" ) :
        """ Get all available vars from the specified UPS
The result is a dictionary containing 'key->val' pairs of all
available vars.
        """
        ups_ascii=ups.encode('ascii')
        if self.__debug :
            print( "[DEBUG] GetUPSVars called..." )

        self.__srv_handler.write( b"LIST VAR %s\n" % ups_ascii )
        result = self.__srv_handler.read_until( b"\n" ).decode('ascii')
        if (result != "BEGIN LIST VAR %s\n" % ups ) :
            ups_vars = "ERR"
            #raise PyNUTError( result.replace( "\n", "" ) )

        else :
            ups_vars   = {}
            result     = (self.__srv_handler.read_until( b"END LIST VAR %s\n" % ups_ascii )).decode('ascii')
            offset     = len( "VAR %s " % ups )
            end_offset = 0 - ( len( "END LIST VAR %s\n" % ups ) + 1 )
    
            for current in result[:end_offset].split( "\n" ) :
                var  = current[ offset: ].split( '"' )[0].replace( " ", "" )
                data = current[ offset: ].split( '"' )[1]
                ups_vars[ var ] = data

        return( ups_vars )

    def GetUPSCommands( self, ups="" ) :
        """ Get all available commands for the specified UPS
The result is a dict object with command name as key and a description
of the command as value
        """
        ups_ascii=ups.encode('ascii')
        if self.__debug :
            print( "[DEBUG] GetUPSCommands called..." )

        self.__srv_handler.write( b"LIST CMD %s\n" % ups_ascii )
        result = self.__srv_handler.read_until( b"\n" ).decode('ascii')
        if (result != "BEGIN LIST CMD %s\n" % ups ):
            raise PyNUTError( result.replace( "\n", "" ) )

        ups_cmds   = {}
        result     = self.__srv_handler.read_until( b"END LIST CMD %s\n" % ups_ascii ).decode('ascii')
        offset     = len( "CMD %s " % ups )
        end_offset = 0 - ( len( "END LIST CMD %s\n" % ups ) + 1 )

        for current in result[:end_offset].split( "\n" ) :
            var  = current[ offset: ].split( '"' )[0].replace( " ", "" )

            # For each var we try to get the available description
            try :
                self.__srv_handler.write( b"GET CMDDESC " + ups_ascii + var.encode('ascii')+ b"\n" )
                temp = self.__srv_handler.read_until( b"\n" )
                if temp[:7] != "CMDDESC" :
                    raise PyNUTError
                else :
                    off  = len( "CMDDESC %s %s " % ( ups, var ) )
                    desc = temp[off:-1].split('"')[1]
            except :
                desc = var

            ups_cmds[ var ] = desc

        return( ups_cmds )

    def GetRWVars( self,  ups="" ) :
        """ Get a list of all writable vars from the selected UPS
The result is presented as a dictionary containing 'key->val' pairs
        """
        ups_ascii=ups.encode('ascii')
        if self.__debug :
            print( "[DEBUG] GetUPSVars from '%s'..." % ups_ascii )

        self.__srv_handler.write( b"LIST RW %s\n" % ups_ascii )
        result = self.__srv_handler.read_until( b"\n" ).decode('ascii')
        if ( result != "BEGIN LIST RW %s\n" % ups ) :
            raise PyNUTError( result.replace( "\n",  "" ) )

        result     = self.__srv_handler.read_until( b"END LIST RW %s\n" % ups_ascii ).decode('ascii')
        offset     = len( "VAR %s" % ups )
        end_offset = 0 - ( len( "END LIST RW %s\n" % ups ) + 1 )
        rw_vars    = {}

        try :
            for current in result[:end_offset].split( "\n" ) :
                var  = current[ offset: ].split( '"' )[0].replace( " ", "" )
                data = current[ offset: ].split( '"' )[1]
                rw_vars[ var ] = data

        except :
            pass

        return( rw_vars )

    def SetRWVar( self, ups="", var="", value="" ):
        """ Set a variable to the specified value on selected UPS
The variable must be a writable value (cf GetRWVars) and you must have the proper
rights to set it (maybe login/password).
        """
        ups = ups.encode('ascii')
        var = var.encode('ascii')
        value = value.encode('ascii')
        self.__srv_handler.write( b"SET VAR %s %s %s\n" % ( ups, var, value ) )
        result = self.__srv_handler.read_until( b"\n" ).decode('ascii')
        if ( result == "OK\n" ) :
            return( "OK" )
        else :
            raise PyNUTError( result )

    def RunUPSCommand( self, ups="", command="" ) :
        """ Send a command to the specified UPS
Returns OK on success or raises an error
        """

        if self.__debug :
            print( "[DEBUG] RunUPSCommand called..." )

        ups = ups.encode('ascii')
        command = command.encode('ascii')
        self.__srv_handler.write( b"INSTCMD %s %s\n" % ( ups, command ) )
        result = self.__srv_handler.read_until( b"\n" ).decode('ascii')
        if ( result == "OK\n" ) :
            return( "OK" )
        else :
            raise PyNUTError( result.replace( "\n", "" ) )

    def FSD( self, ups="") :
        """ Send FSD command
Returns OK on success or raises an error
        """
        ups_ascii=ups.encode('ascii')
        if self.__debug :
            print( "[DEBUG] MASTER called..." )

        self.__srv_handler.write( b"MASTER %s\n" % ups_ascii )
        result = self.__srv_handler.read_until( b"\n" ).decode('ascii')
        if ( result != "OK MASTER-GRANTED\n" ) :
            raise PyNUTError( ( "Master level function are not available", "" ) )

        if self.__debug :
            print( "[DEBUG] FSD called..." )
        self.__srv_handler.write( "FSD %s\n" % ups_ascii )
        result = self.__srv_handler.read_until( b"\n" ).decode('ascii')
        if ( result == "OK FSD-SET\n" ) :
            return( "OK" )
        else :
            raise PyNUTError( result.replace( "\n", "" ) )

    def help(self) :
        """ Send HELP command
        """

        if self.__debug :
            print( "[DEBUG] HELP called..." )

        self.__srv_handler.write( b"HELP\n")
        return self.__srv_handler.read_until( b"\n" ).decode('ascii')

    def ver(self) :
        """ Send VER command
        """

        if self.__debug :
            print( "[DEBUG] VER called..." )

        self.__srv_handler.write( b"VER\n")
        return self.__srv_handler.read_until( "\n" ).decode('ascii')

    def ListClients( self, ups = None ) :
        """ Returns the list of connected clients from the NUT server
The result is a dictionary containing 'key->val' pairs of 'UPSName' and a list of clients
        """
        ups_ascii=ups.encode('ascii')
        if self.__debug :
            print( "[DEBUG] ListClients from server" )

        if ups and (ups not in self.GetUPSList()):
            raise PyNUTError( "%s is not a valid UPS" % ups )

        if ups:
            self.__srv_handler.write( b"LIST CLIENTS %s\n" % ups_ascii)
        else:
            self.__srv_handler.write( b"LIST CLIENTS\n" )
        result = self.__srv_handler.read_until( b"\n" ).decode('ascii')
        if result != "BEGIN LIST CLIENTS\n" :
            raise PyNUTError( result.replace( "\n", "" ) )

        result = self.__srv_handler.read_until( b"END LIST CLIENTS\n" ).decode('ascii')
        ups_list = {}

        for line in result.split( "\n" ):
            if line[:6] == "CLIENT" :
                host, ups = line[7:].split(' ')
                ups.replace(' ', '')
                if not ups in ups_list:
                    ups_list[ups] = []
                ups_list[ups].append(host)

       return( ups_list )
