import aes128
import Print
import os
import shutil
import json
from Fs import Nsp as squirrelNSP
from Fs import Xci as squirrelXCI
from Fs.Nca import NcaHeader
from Fs.File import MemoryFile
import sq_tools
import io
from Fs import Type as FsType
from Fs import factory
import Keys
from binascii import hexlify as hx, unhexlify as uhx
from DBmodule import Exchange as exchangefile
import math
import sys
import subprocess
from mtp.wpd import is_switch_connected
import listmanager
import csv
from colorama import Fore, Back, Style
import time
if not is_switch_connected():
	sys.exit("Switch device isn't connected.\nCheck if mtp responder is running!!!")	
	
bucketsize = 81920

# SET ENVIRONMENT
squirrel_dir=os.path.abspath(os.curdir)
NSCB_dir=os.path.abspath('../'+(os.curdir))

if os.path.exists(os.path.join(squirrel_dir,'ztools')):
	NSCB_dir=squirrel_dir
	zconfig_dir=os.path.join(NSCB_dir, 'zconfig')	  
	ztools_dir=os.path.join(NSCB_dir,'ztools')
	squirrel_dir=ztools_dir
elif os.path.exists(os.path.join(NSCB_dir,'ztools')):
	squirrel_dir=squirrel_dir
	ztools_dir=os.path.join(NSCB_dir, 'ztools')
	zconfig_dir=os.path.join(NSCB_dir, 'zconfig')
else:	
	ztools_dir=os.path.join(NSCB_dir, 'ztools')
	zconfig_dir=os.path.join(NSCB_dir, 'zconfig')

testroute1=os.path.join(squirrel_dir, "squirrel.py")
testroute2=os.path.join(squirrel_dir, "squirrel.exe")
urlconfig=os.path.join(zconfig_dir,'NUT_DB_URL.txt')
isExe=False
if os.path.exists(testroute1):
	squirrel=testroute1
	isExe=False
elif os.path.exists(testroute2):	
	squirrel=testroute2
	isExe=True
bin_folder=os.path.join(ztools_dir, 'bin')
nscb_mtp=os.path.join(bin_folder, 'nscb_mtp.exe')
cachefolder=os.path.join(ztools_dir, '_mtp_cache_')
if not os.path.exists(cachefolder):
	os.makedirs(cachefolder)
games_installed_cache=os.path.join(cachefolder, 'games_installed.txt')
mtp_source_lib=os.path.join(zconfig_dir,'mtp_source_libraries.txt')
mtp_internal_lib=os.path.join(zconfig_dir,'mtp_SD_libraries.txt')
storage_info=os.path.join(cachefolder, 'storage.csv')

def file_verification(filename,hash=False):
	if not os.path.exists(cachefolder):
		os.makedirs(cachefolder)
	tempfolder=os.path.join(cachefolder, 'temp')	
	if not os.path.exists(tempfolder):
		os.makedirs(tempfolder)	
	verdict=False;isrestored=False;cnmt_is_patched=False
	if filename.endswith('.nsp') or filename.endswith('.nsx') or filename.endswith('.nsz') or filename.endswith('.xcz') or filename.endswith('.xci'):
		try:
			if filename.endswith('.nsp') or filename.endswith('.nsx') or filename.endswith('.nsz'):		
				f = squirrelNSP(filename, 'rb')
			elif filename.endswith('.xci') or filename.endswith('.xcz'):	
				f = factory(filename)		
				f.open(filename, 'rb')	
			check,feed=f.verify()
			if filename.endswith('.nsp') or filename.endswith('.nsx') or filename.endswith('.nsz'):					
				verdict,headerlist,feed=f.verify_sig(feed,tempfolder,cnmt='nocheck')
			else:
				verdict,headerlist,feed=f.verify_sig(feed,tempfolder)
			output_type='nsp';multi=False;cnmtcount=0
			if verdict == True:
				isrestored=True
				for i in range(len(headerlist)):
					entry=headerlist[i]
					if str(entry[0]).endswith('.cnmt.nca'):
						cnmtcount+=1
						if cnmt_is_patched==False:
							status=entry[2]
							if status=='patched':
								cnmt_is_patched=True
					if entry[1]!=False:
						if int(entry[-1])==1:
							output_type='xci'
						isrestored=False	
					else:
						pass
				if	isrestored == False:	
					if cnmt_is_patched !=True:
						print('\nFILE VERIFICATION CORRECT.\n -> FILE WAS MODIFIED BUT ORIGIN IS CONFIRMED AS LEGIT\n')
					else:
						print('\nFILE VERIFICATION CORRECT. \n -> FILE WAS MODIFIED AND CNMT PATCHED\n')
				else:
					print("\nFILE VERIFICATION CORRECT. FILE IS SAFE.\n")
			if verdict == False:		
				print("\nFILE VERIFICATION INCORRECT. \n -> UNCONFIRMED ORIGIN FILE HAS BEEN TAMPERED WITH\n")	
			if 	hash==True and verdict==True:
				if filename.endswith('.nsp') or filename.endswith('.nsx') or filename.endswith('.xci'):
					verdict,feed=f.verify_hash_nca(65536,headerlist,verdict,feed)
				elif filename.endswith('.nsz'):
					verdict,feed=f.nsz_hasher(65536,headerlist,verdict,feed)
				elif filename.endswith('.xcz'):	
					verdict,feed=f.xcz_hasher(65536,headerlist,verdict,feed)
			f.flush()
			f.close()					
		except BaseException as e:
			Print.error('Exception: ' + str(e))
	return verdict,isrestored,cnmt_is_patched
		
def install(filepath=None,destiny="SD",verification=True,outfolder=None,ch_medium=True,check_fw=True,patch_keygen=False):	
	kgwarning=False;dopatch=False;keygeneration=0;tgkg=0
	if filepath=="":
		filepath=None
	if filepath==None:
		print("File input = null")
		return False
	if verification==True or str(verification).upper()=="HASH":	
		if str(verification).upper()=="HASH":
			verdict,isrestored,cnmt_is_patched=file_verification(filepath,hash=True)		
		else:
			verdict,isrestored,cnmt_is_patched=file_verification(filepath)
		if verdict==False:
			print("File didn't pass verification. Skipping...")
			return False
	print("- Retrieving Space on device")
	SD_ds,SD_fs,NAND_ds,NAND_fs,FW,device=get_storage_info()
	print("- Calculating Installed size")	
	dbDict=get_DB_dict(filepath)
	installedsize=dbDict['InstalledSize']	
	if check_fw==True:	
		keygeneration=dbDict['keygeneration']
		if FW!='unknown':	
			try:
				FW_RSV,RRSV=sq_tools.transform_fw_string(FW)
				FW_kg=sq_tools.kg_by_RSV(FW_RSV)
			except BaseException as e:
				Print.error('Exception: ' + str(e))
				FW='unknown'
				FW_kg='unknown'
				pass
		if FW!='unknown' and FW_kg!='unknown':			
			if int(keygeneration)>int(FW_kg):
				kgwarning=True
				tgkg=int(FW_kg)
			else:
				tgkg=keygeneration
		else:
			tgkg=keygeneration
		print(f"- Console Firmware: {FW} ({FW_RSV}) - keygen {FW_kg})")		
		print(f"- File keygeneration: {keygeneration}")				
	if kgwarning==True and patch_keygen==False:
		print("File requires a higher firmware. Skipping...")
		return False		
	elif kgwarning==True and patch_keygen==True: 	
		print("File requires a higher firmware. It'll will be prepatch")
		dopatch=True	
	if destiny=="SD":
		print(f"  * SD free space: {SD_fs} ({sq_tools.getSize(SD_fs)})")	
		print(f"  * File installed size: {installedsize} ({sq_tools.getSize(installedsize)})")		
		if installedsize>SD_fs:
			if installedsize<NAND_fs and ch_medium==True:
				print("  Not enough space on SD. Changing target to EMMC")
				print(f"  * EMMC free space: {NAND_fs} ({sq_tools.getSize(NAND_fs)})")						
				destiny="NAND"
			elif  ch_medium==False:	
				sys.exit("   NOT ENOUGH SPACE SD STORAGE")				
			else:
				sys.exit("   NOT ENOUGH SPACE ON DEVICE")				
	else:
		print(f"  * EMMC free space: {NAND_fs} ({sq_tools.getSize(NAND_fs)})")	
		print(f"  * File installed size: {installedsize} ({sq_tools.getSize(installedsize)})")		
		if installedsize>NAND_fs:		
			if installedsize<SD_fs and ch_medium==True:
				print("  Not enough space on EMMC. Changing target to SD")			
				print(f"  * SD free space: {SD_fs} ({sq_tools.getSize(SD_fs)})")					
				destiny="SD"
			elif  ch_medium==False:	
				sys.exit("   NOT ENOUGH SPACE EMMC STORAGE")							
			else:
				sys.exit("   NOT ENOUGH SPACE ON DEVICE")
	if filepath.endswith('xci') or dopatch==True:
		install_converted(filepath=filepath,outfolder=outfolder,destiny=destiny,kgpatch=dopatch,tgkg=keygeneration)
		return	
	process=subprocess.Popen([nscb_mtp,"Install","-ori",filepath,"-dst",destiny])
	while process.poll()==None:
		if process.poll()!=None:
			process.terminate();
			
def install_conv_st1(filepath,outfolder,keypatch='false'):
	tname=str(os.path.basename(filepath))[:-3]+'nsp'
	tmpfile=os.path.join(outfolder,tname)
	if filepath.endswith('xci'):
		f = factory(filepath)
		f.open(filepath, 'rb')
	elif filepath.endswith('nsp'):	
		f = squirrelNSP(filepath, 'rb')	
	f.c_nsp_direct(65536,tmpfile,outfolder,keypatch=keypatch)
	f.flush()
	f.close()	
			
def install_converted(filepath=None,outfolder=None,destiny="SD",kgpatch=False,tgkg=0):		
	if filepath=="":
		filepath=None	
	if outfolder=="":
		filepath=None	
	if outfolder==None:
		outfolder=cachefolder
		if not os.path.exists(cachefolder):
			os.makedirs(cachefolder)	
	if kgpatch==False:
		keypatch='false'
	else:
		keypatch=int(tgkg)
	if filepath==None:
		print("File input = null")
		return False
	if not os.path.exists(outfolder):
		os.makedirs(outfolder)		
	for f in os.listdir(outfolder):
		fp = os.path.join(outfolder, f)
		try:
			shutil.rmtree(fp)
		except OSError:
			os.remove(fp)		
	tname=str(os.path.basename(filepath))[:-3]+'nsp'
	tmpfile=os.path.join(outfolder,tname)	
	if isExe==False:
		process0=subprocess.Popen([sys.executable,squirrel,"-lib_call","mtp.mtpinstaller","install_conv_st1","-xarg",filepath,outfolder,keypatch])	
	else:
		process0=subprocess.Popen([squirrel,"-lib_call","mtp.mtpinstaller","install_conv_st1","-xarg",filepath,outfolder,keypatch])		
	while process0.poll()==None:
		if process0.poll()!=None:
			process0.terminate();
	process=subprocess.Popen([nscb_mtp,"Install","-ori",tmpfile,"-dst",destiny])		
	while process.poll()==None:
		if process.poll()!=None:
			process.terminate();	
	try:			
		for f in os.listdir(outfolder):
			fp = os.path.join(outfolder, f)
			try:
				shutil.rmtree(fp)
			except OSError:
				os.remove(fp)	
	except:pass				
		
def loop_install(tfile,destiny="SD",verification=True,outfolder=None,ch_medium=True,check_fw=True,patch_keygen=False,ch_base=False,ch_other=False,checked=False):		
	if not os.path.exists(tfile):
		sys.exit(f"Couldn't find {tfile}")		
	if (ch_base==True or ch_other==True) and checked==False:		
		print("Content check activated")			
		retrieve_installed()
		installed=parsedinstalled()
	elif (ch_base==True or ch_other==True) and checked==True:	
		print("Content check activated. Games are preparsed")		
		installed=parsedinstalled()	
	file_list=listmanager.read_lines_to_list(tfile,all=True)
	for item in file_list:
		if ch_base==True or ch_other==True:
			fileid,fileversion,cctag,nG,nU,nD,baseid=listmanager.parsetags(item)
			if fileid.endswith('000') and fileversion==0 and fileid in installed.keys() and ch_base==True:
				print("Base game already installed. Skipping...")
				listmanager.striplines(tfile,counter=True)
				continue
			elif fileid.endswith('000') and fileid in installed.keys() and ch_other==True:
				updid=fileid[:-3]+'800'
				if fileversion>((installed[fileid])[2]):
					print("Asking DBI to delete previous content")
					process=subprocess.Popen([nscb_mtp,"DeleteID","-ID",fileid])	
					while process.poll()==None:
						if process.poll()!=None:
							process.terminate();					
					process=subprocess.Popen([nscb_mtp,"DeleteID","-ID",updid])		
					while process.poll()==None:
						if process.poll()!=None:
							process.terminate();					
				else:
					print("The update is a previous version than the installed on device.Skipping..")
					listmanager.striplines(tfile,counter=True)
					continue				
			elif ch_other==True	and fileid in installed.keys():
				if fileversion>((installed[fileid])[2]):
					print("Asking DBI to delete previous update")
					process=subprocess.Popen([nscb_mtp,"DeleteID","-ID",fileid])					
					while process.poll()==None:
						if process.poll()!=None:
							process.terminate();
				else:
					print("The update is a previous version than the installed on device.Skipping..")
					listmanager.striplines(tfile,counter=True)
					continue					
		install(filepath=item,destiny=destiny,verification=verification,outfolder=outfolder,ch_medium=ch_medium,check_fw=check_fw,patch_keygen=patch_keygen)
		print("")
		listmanager.striplines(tfile,counter=True)
		
def retrieve_installed():	
	print("  * Parsing games in device. Please Wait...")			
	process=subprocess.Popen([nscb_mtp,"ShowInstalled","-tfile",games_installed_cache,"-show","false","-exci","true"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	while process.poll()==None:
		if process.poll()!=None:
			process.terminate();	
	if os.path.exists(games_installed_cache):	
		print("   Success")		
			
def parsedinstalled(exclude_xci=True):
	installed={}	
	if os.path.exists(games_installed_cache):	
		gamelist=listmanager.read_lines_to_list(games_installed_cache,all=True)	
		for g in gamelist:
			if exclude_xci==True:
				if g.endswith('xci') or g.endswith('xc0'):
					continue
			entry=listmanager.parsetags(g)
			entry=list(entry)		
			entry.append(g)
			installed[entry[0]]=entry
	return installed	
	
		
def get_installed_info(tfile=None,search_new=True,excludehb=True):
	if not os.path.exists(cachefolder):
		os.makedirs(cachefolder)
	forecombo=Style.BRIGHT+Back.GREEN+Fore.WHITE
	if tfile=="":
		tfile=None
	if os.path.exists(games_installed_cache):
		try:
			os.remove(games_installed_cache)
		except:pass
	if tfile==None:
		for f in os.listdir(cachefolder):
			fp = os.path.join(cachefolder, f)
			try:
				shutil.rmtree(fp)
			except OSError:
				os.remove(fp)	
		process=subprocess.Popen([nscb_mtp,"ShowInstalled","-tfile",games_installed_cache,"-show","false"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		print("Parsing games in device. Please Wait...")
		while process.poll()==None:
			if process.poll()!=None:
				process.terminate();	
	if os.path.exists(games_installed_cache):	
		gamelist=listmanager.read_lines_to_list(games_installed_cache,all=True)
		gamelist.sort()
		print("..........................................................")
		print("CONTENT FOUND ON DEVICE")
		print("..........................................................")		
		installed={}
		for g in gamelist:
			fileid,fileversion,cctag,nG,nU,nD,baseid=listmanager.parsetags(g)
			g0=[pos for pos, char in enumerate(g) if char == '[']
			g0=(g[0:g0[0]]).strip()
			installed[fileid]=[fileid,fileversion,cctag,nG,nU,nD,baseid,g0,g]
			if len(g0)>33:
				g0=g0[0:30]+'...'					
			if excludehb==True:
				if not fileid.startswith('05') and not fileid.startswith('04')  and not str(fileid).lower()=='unknown':
					if g.endswith('.xci') or g.endswith('.xc0'):
						print(f"{g0}|{fileid}|{fileversion}|XCI|{nG}G|{nU}U|{nD}D")
					else:
						print(f"{g0}|{fileid}|{fileversion}|{cctag}")
			else:
				if g.endswith('.xci') or g.endswith('.xc0'):
					print(f"{g0}|{fileid}|{fileversion}|XCI|{nG}G|{nU}U|{nD}D")	
				else:	
					print(f"{g0}|{fileid}|{fileversion}|{cctag}")
		if search_new==True:			
			import nutdb
			nutdb.check_other_file(urlconfig,'versions_txt')
			f='nutdb_'+'versions'+'.txt'
			DATABASE_folder=nutdb.get_DBfolder()
			_dbfile_=os.path.join(DATABASE_folder,f)
			versiondict={}
			with open(_dbfile_,'rt',encoding='utf8') as csvfile:
				readCSV = csv.reader(csvfile, delimiter='|')	
				i=0			
				for row in readCSV:
					if i==0:
						csvheader=row
						i=1
						if 'id' and 'version' in csvheader:
							id=csvheader.index('id')
							ver=csvheader.index('version')	
						else:break	
					else:	
						try:
							tid=str(row[id]).upper() 
							version=str(row[ver]).upper() 
							if tid.endswith('800'):
								baseid=tid[:-3]+'000'
							if 	baseid in versiondict.keys():
								v=versiondict[baseid]
								if v<int(version):
									versiondict[baseid]=int(version)
							else:
								versiondict[tid]=int(version)
						except:pass		
			print("..........................................................")
			print("NEW UPDATES")
			print("..........................................................")			
			for k in installed.keys():	
				fileid,fileversion,cctag,nG,nU,nD,baseid,g0,g=installed[k]
				if len(g0)>33:
					g0=g0[0:30]+'...'						
				v=0;
				updateid=fileid[:-3]+'800'
				if updateid in installed.keys() and fileid.endswith('000'):				
					continue
				if	fileid.endswith('800'):
					try:			
						v=versiondict[baseid]
					except:pass						
				else:	
					try:
						v=versiondict[fileid]
					except:pass			
				if int(v)>int(fileversion):
					if fileid.endswith('000') or fileid.endswith('800'):
						updid=fileid[:-3]+'800'
						print(f"{g0} [{baseid}][{fileversion}] -> "+forecombo+  f"[{updid}] [v{v}]"+Style.RESET_ALL)
					else:
						print(f"{g0} [{fileid}][{fileversion}] -> "+forecombo+  f"[{fileid}] [v{v}]"+Style.RESET_ALL)	
			print("..........................................................")
			print("NEW DLCS")
			print("..........................................................")	
			for k in versiondict.keys():
				if k in installed.keys() or k.endswith('000') or k.endswith('800'):
					continue
				else:
					baseid=get_dlc_baseid(k)
					updid=baseid[:-3]+'800'
					if baseid in installed.keys() or updid in installed.keys():
						fileid,fileversion,cctag,nG,nU,nD,baseid,g0,g=installed[baseid]
						if len(g0)>33:
							g0=g0[0:30]+'...'						
						print(f"{g0} [{baseid}] -> "+forecombo+ f"[{k}] [v{versiondict[k]}]"+Style.RESET_ALL)
					

def get_archived_info(search_new=True,excludehb=True):	
	forecombo=Style.BRIGHT+Back.GREEN+Fore.WHITE
	if not os.path.exists(cachefolder):
		os.makedirs(cachefolder)	
	for f in os.listdir(cachefolder):
		fp = os.path.join(cachefolder, f)
		try:
			shutil.rmtree(fp)
		except OSError:
			os.remove(fp)	
	print("1. Retrieving registered...")			
	dbicsv=os.path.join(cachefolder,"registered.csv")
	process=subprocess.Popen([nscb_mtp,"Download","-ori","4: Installed games\\InstalledApplications.csv","-dst",dbicsv],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	while process.poll()==None:
		if process.poll()!=None:
			process.terminate();
	if os.path.exists(dbicsv):	
		print("   Success")			
	print("2. Checking Installed...")
	process=subprocess.Popen([nscb_mtp,"ShowInstalled","-tfile",games_installed_cache,"-show","false"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	while process.poll()==None:
		if process.poll()!=None:
			process.terminate();	
	if os.path.exists(games_installed_cache):	
		print("   Success")
	gamelist=listmanager.read_lines_to_list(games_installed_cache,all=True)	
	with open(dbicsv,'rt',encoding='utf8') as csvfile:
		readCSV = csv.reader(csvfile, delimiter=',')
		id=0;ver=1;tname=2;
		dbi_dict={}
		for row in readCSV:		
			try:
				tid=(str(row[id]).upper())[2:]
				version=int(row[ver])
				name=str(row[tname])
				dbi_dict[tid]=[tid,version,name]
			except:pass
	installed={}		
	for g in gamelist:
		entry=listmanager.parsetags(g)
		installed[entry[0]]=entry
	print("..........................................................")
	print("ARCHIVED|REGISTERED GAMES")
	print("..........................................................")			
	for g in dbi_dict.keys():
		if not g in installed.keys():
			tid,version,name=dbi_dict[g]
			if len(name)>33:
				name=name[0:30]+'...'							
			print(f"{name} [{tid}][{version}]")
	if search_new==True:			
		import nutdb
		nutdb.check_other_file(urlconfig,'versions_txt')
		f='nutdb_'+'versions'+'.txt'
		DATABASE_folder=nutdb.get_DBfolder()
		_dbfile_=os.path.join(DATABASE_folder,f)
		versiondict={}
		with open(_dbfile_,'rt',encoding='utf8') as csvfile:
			readCSV = csv.reader(csvfile, delimiter='|')	
			i=0			
			for row in readCSV:
				if i==0:
					csvheader=row
					i=1
					if 'id' and 'version' in csvheader:
						id=csvheader.index('id')
						ver=csvheader.index('version')	
					else:break	
				else:	
					try:
						tid=str(row[id]).upper() 
						version=str(row[ver]).upper() 
						if tid.endswith('800'):
							baseid=tid[:-3]+'000'
						if 	baseid in versiondict.keys():
							v=versiondict[baseid]
							if v<int(version):
								versiondict[baseid]=int(version)
						else:
							versiondict[tid]=int(version)
					except:pass		
		print("..........................................................")
		print("NEW UPDATES")
		print("..........................................................")			
		for k in dbi_dict.keys():	
			fileid,fileversion,g0=dbi_dict[k]
			if len(g0)>33:
				g0=g0[0:30]+'...'
			v=0;
			updateid=fileid[:-3]+'800'
			if updateid in dbi_dict.keys() and fileid.endswith('000'):				
				continue
			if	fileid.endswith('800'):
				try:			
					v=versiondict[baseid]
				except:pass						
			else:	
				try:
					v=versiondict[fileid]
				except:pass			
			if int(v)>int(fileversion):
				if fileid.endswith('000') or fileid.endswith('800'):
					updid=fileid[:-3]+'800'
					print(f"{g0} [{baseid}][{fileversion}] -> "+forecombo+  f"[{updid}] [v{v}]"+Style.RESET_ALL)
				else:
					print(f"{g0} [{fileid}][{fileversion}] -> "+forecombo+  f"[{fileid}] [v{v}]"+Style.RESET_ALL)	
		print("..........................................................")
		print("NEW DLCS")
		print("..........................................................")	
		for k in versiondict.keys():
			if k in dbi_dict.keys() or k.endswith('000') or k.endswith('800'):
				continue
			else:
				baseid=get_dlc_baseid(k)
				updid=baseid[:-3]+'800'
				if baseid in dbi_dict.keys() or updid in dbi_dict.keys():
					fileid,fileversion,g0=dbi_dict[baseid]
					if len(g0)>33:
						g0=g0[0:30]+'...'				
					print(f"{g0} [{baseid}] -> "+forecombo+ f"[{k}] [v{versiondict[k]}]"+Style.RESET_ALL)			
			

def update_console(libraries="all",destiny="SD",exclude_xci=True,prioritize_nsz=True,tfile=None,verification=True,ch_medium=True,ch_other=False):	
	if tfile==None:
		tfile=os.path.join(NSCB_dir, 'MTP1.txt')
	if os.path.exists(tfile):
		try:
			os.remove(tfile)
		except: pass			
	libdict=get_libs("source");
	pths={}	
	if libraries=="all":
		for entry in libdict.keys():
			pths[entry]=((libdict[entry])[0])
	else:
		for entry in libdict.keys():
			if (libdict[entry])[1]==True:
				pths[entry]=((libdict[entry])[0])	
	if not os.path.exists(cachefolder):
		os.makedirs(cachefolder)				
	for f in os.listdir(cachefolder):
		fp = os.path.join(cachefolder, f)
		try:
			shutil.rmtree(fp)
		except OSError:
			os.remove(fp)	
	print("1. Parsing games in device. Please Wait...")			
	process=subprocess.Popen([nscb_mtp,"ShowInstalled","-tfile",games_installed_cache,"-show","false"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	while process.poll()==None:
		if process.poll()!=None:
			process.terminate();	
	if os.path.exists(games_installed_cache):	
		print("   Success")
	gamelist=listmanager.read_lines_to_list(games_installed_cache,all=True)
	installed={}		
	for g in gamelist:
		if exclude_xci==True:
			if g.endswith('xci') or g.endswith('xc0'):
				continue
		entry=listmanager.parsetags(g)
		entry=list(entry)		
		entry.append(g)
		installed[entry[0]]=entry	
	print("2. Parsing local libraries. Please Wait...")				
	locallist=[]
	for p in pths.keys():
		locallist+=listmanager.folder_to_list(pths[p],['nsp','nsz'])
		print(f'   Parsed Library: "{str(p).upper()}"')		
	if prioritize_nsz==True:
		locallist=sorted(locallist, key=lambda x: x[-1])
		locallist.reverse()
	localgames={}		
	for g in locallist:
		entry=listmanager.parsetags(g)
		entry=list(entry)
		entry.append(g)		
		if not entry[0] in localgames:
			localgames[entry[0]]=entry
		else:
			v=(localgames[entry[0]])[1]
			if int(entry[1])>int(v):
				localgames[entry[0]]=entry		
	print("3. Searching new updates. Please Wait...")						
	gamestosend={}		
	for g in installed.keys():
		if g.endswith('000') or g.endswith('800'): 
			try:
				updid=g[:-3]+'800'
				if updid in localgames:
					if updid in installed:
						if ((installed[updid])[1])<((localgames[updid])[1]):
							if not updid in gamestosend:
								gamestosend[updid]=localgames[updid]
							else:
								if ((gamestosend[updid])[1])<((localgames[updid])[1]):
									gamestosend[updid]=localgames[updid]
					else:
						if not updid in gamestosend:
							gamestosend[updid]=localgames[updid]
						else:
							if ((gamestosend[updid])[1])<((localgames[updid])[1]):
								gamestosend[updid]=localgames[updid]								
			except:pass
		else:
			try:		
				if g in localgames:
					if ((installed[g])[1])<((localgames[g])[1]):
						if not g in gamestosend:
							gamestosend[g]=localgames[g]
						else:
							if ((gamestosend[g])[1])<((localgames[g])[1]):
								gamestosend[g]=localgames[g]
			except:pass							
	print("4. Searching new dlcs. Please Wait...")	
	for g in installed.keys():	
		try:
			if g.endswith('000') or g.endswith('800'): 
				baseid=g[:-3]+'000'
			else:
				baseid=(installed[g])[6]
			for k in localgames.keys():
				try:				
					if not (k.endswith('000') or k.endswith('800')) and not k in installed:
						test=get_dlc_baseid(k)
						if baseid ==test:
							if not k in gamestosend:
								gamestosend[k]=localgames[k]
							else:
								if ((gamestosend[k])[1])<((localgames[k])[1]):
									gamestosend[k]=localgames[k]	
				except BaseException as e:
					# Print.error('Exception: ' + str(e))			
					pass								
		except BaseException as e:
			# Print.error('Exception: ' + str(e))			
			pass
	print("5. List of content that will get installed...")	
	gamepaths=[]
	if len(gamestosend.keys())>0:
		for i in sorted(gamestosend.keys()):
			fileid,fileversion,cctag,nG,nU,nD,baseid,path=gamestosend[i]
			bname=os.path.basename(path) 
			gamepaths.append(path)
			g0=[pos for pos, char in enumerate(bname) if char == '[']	
			g0=(bname[0:g0[0]]).strip()
			print(f"   * {g0} [{fileid}][{fileversion}] [{cctag}] - {(bname[-3:]).upper()}")
		print("6. Generating text file...")		
		with open(tfile,'w', encoding='utf8') as textfile:
			for i in gamepaths:
				textfile.write((i).strip()+"\n")
		print("7. Triggering installer on loop mode.")
		print("   Note:If you interrupt the list use normal install mode to continue list")				
		loop_install(tfile,destiny=destiny,verification=verification,ch_medium=ch_medium,ch_other=ch_other,checked=True)
	else:
		print("\n   --- DEVICE IS UP TO DATE ---")		
	
def get_libs(lib="source"):
	libraries={}
	if lib=="source":
		libtfile=mtp_source_lib
	else:
		libtfile=mtp_internal_lib	
	with open(libtfile,'rt',encoding='utf8') as csvfile:
		readCSV = csv.reader(csvfile, delimiter='|')	
		i=0;up=False	
		for row in readCSV:
			if i==0:
				csvheader=row
				i=1
				if 'library_name' and 'path' and 'Update' in csvheader:
					lb=csvheader.index('library_name')
					pth=csvheader.index('path')	
					up=csvheader.index('Update')	
				else:
					if 'library_name' and 'path' in csvheader:
						lb=csvheader.index('library_name')
						pth=csvheader.index('path')				
					else:break	
			else:	
				try:
					update=False
					library=str(row[lb])
					route=str(row[pth])			
					if up!=False:
						update=str(row[up])
						if update.upper()=="TRUE":
							update=True
						else:
							update=False
					else:
						update=False
					libraries[library]=[route,update]
				except:pass	
	return libraries		
			
def get_dlc_baseid(titleid):
	baseid=str(titleid)
	token=int(hx(bytes.fromhex('0'+baseid[-4:-3])),16)-int('1',16)
	token=str(hex(token))[-1]
	token=token.upper()
	baseid=baseid[:-4]+token+'000'	
	return baseid	

def get_storage_info():
	SD_ds=0;SD_fs=0;NAND_ds=0;NAND_fs=0;device='unknown';FW='unknown'
	if os.path.exists(storage_info):
		try:
			os.remove(storage_info)
		except:pass	
	process=subprocess.Popen([nscb_mtp,"ReportStorage","-tfile",storage_info],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	while process.poll()==None:
		if process.poll()!=None:
			process.terminate();
	if os.path.exists(storage_info):
		with open(storage_info,'rt',encoding='utf8') as csvfile:
			readCSV = csv.reader(csvfile, delimiter='|')	
			i=0			
			for row in readCSV:
				if i==0:
					csvheader=row
					i=1
					if 'device' and 'disk_name' and 'capacity' and 'freespace' and 'FW' in csvheader:
						idev=csvheader.index('device')
						idn=csvheader.index('disk_name')
						idc=csvheader.index('capacity')
						ifs=csvheader.index('freespace')
						ifw=csvheader.index('FW')						
					else:break		
				else:
					if i==1:
						try:
							device=str(row[idev])
							FW=str(row[ifw])
						except:pass	
						i+1;
					if 'SD CARD' in str(row[idn]).upper() or 'SD' in str(row[idn]).upper():
						# print(str(row[idn]));print(str(row[idc]));print(str(row[ifs]));
						SD_ds=int(row[idc])
						SD_fs=int(row[ifs])
					if 'USER' in str(row[idn]).upper():							
						# print(str(row[idn]));print(str(row[idc]));print(str(row[ifs]));
						NAND_ds=int(row[idc])
						NAND_fs=int(row[ifs])
					if str(row[idev]).upper()=="TINFOIL":
						SD_ds=int(row[idc])
						SD_fs=int(row[ifs])
						NAND_ds=0
						NAND_fs=0
	return SD_ds,SD_fs,NAND_ds,NAND_fs,FW,device
	
def get_DB_dict(filepath):
	installedsize=0
	if filepath.endswith('xci') or filepath.endswith('xcz'):
		f = factory(filepath)		
		f.open(filepath, 'rb')		
		dict=f.return_DBdict()			
		f.flush()
		f.close()
	elif filepath.endswith('nsp') or filepath.endswith('nsz') or filepath.endswith('nsx'):
		f = squirrelNSP(filepath)			
		dict=f.return_DBdict()		
		f.flush()
		f.close()		
	return dict