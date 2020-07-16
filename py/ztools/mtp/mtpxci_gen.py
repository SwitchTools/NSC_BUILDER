import aes128
import Print
import os
import shutil
import json
import listmanager
from Fs import Nsp as squirrelNSP
from Fs import Xci as squirrelXCI
from Fs import factory
from Fs.Nca import NcaHeader
from Fs import Nca
from Fs.File import MemoryFile
from Fs import Ticket
import sq_tools
import io
from Fs import Type as FsType
import Keys
from binascii import hexlify as hx, unhexlify as uhx
from DBmodule import Exchange as exchangefile
import math
import subprocess
import sys
from mtp.wpd import is_switch_connected
from python_pick import pick
from python_pick import Picker
import csv
from tqdm import tqdm
import Print

def check_connection():
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
valid_saves_cache=os.path.join(cachefolder, 'valid_saves.txt')
mtp_source_lib=os.path.join(zconfig_dir,'mtp_source_libraries.txt')
mtp_internal_lib=os.path.join(zconfig_dir,'mtp_SD_libraries.txt')
storage_info=os.path.join(cachefolder, 'storage.csv')
download_lib_file = os.path.join(zconfig_dir, 'mtp_download_libraries.txt')

def get_header_size(flist):
	properheadsize=0;sz=0;total_list=[]
	for filepath in flist:
		if filepath.endswith('xci') or filepath.endswith('xcz'):
			files_list=sq_tools.ret_xci_offsets(filepath)
			joined_list = [*total_list, *files_list]
			total_list=joined_list
			files=list();filesizes=list()
			fplist=list()
			for k in range(len(files_list)):
				entry=files_list[k]
				fplist.append(entry[0])
			for i in range(len(files_list)):
				entry=files_list[i]
				cnmtfile=entry[0]
				if cnmtfile.endswith('.cnmt.nca'):
					f=squirrelXCI(filepath)
					titleid,titleversion,base_ID,keygeneration,rightsId,RSV,RGV,ctype,metasdkversion,exesdkversion,hasHtmlManual,Installedsize,DeltaSize,ncadata=f.get_data_from_cnmt(cnmtfile)
					for j in range(len(ncadata)):
						row=ncadata[j]
						# print(row)
						if row['NCAtype']!='Meta':
							test1=str(row['NcaId'])+'.nca';test2=str(row['NcaId'])+'.ncz'
							if test1 in fplist or test2 in fplist:
								# print(str(row['NcaId'])+'.nca')
								files.append(str(row['NcaId'])+'.nca')
								filesizes.append(int(row['Size']))	
								sz+=int(row['Size'])		
						elif row['NCAtype']=='Meta':
							# print(str(row['NcaId'])+'.cnmt.nca')
							files.append(str(row['NcaId'])+'.cnmt.nca')
							filesizes.append(int(row['Size']))	
							sz+=int(row['Size'])
			sec_hashlist=list()
			try:
				for file in files:
					sha,size,gamecard=f.file_hash(file)
					# print(sha)
					if sha != False:
						sec_hashlist.append(sha)	
			except BaseException as e:
				Print.error('Exception: ' + str(e))									
			f.flush()
			f.close()	
			xci_header,game_info,sig_padding,xci_certificate,root_header,upd_header,norm_header,sec_header,rootSize,upd_multiplier,norm_multiplier,sec_multiplier=sq_tools.get_xciheader(files,filesizes,sec_hashlist)			
			outheader=xci_header
			outheader+=game_info
			outheader+=sig_padding
			outheader+=xci_certificate
			outheader+=root_header
			outheader+=upd_header
			outheader+=norm_header
			outheader+=sec_header		
		elif filepath.endswith('nsp') or filepath.endswith('nsz'):
			files_list=sq_tools.ret_nsp_offsets(filepath)
			joined_list = [*total_list, *files_list]
			total_list=joined_list			
			files=list();filesizes=list()
			fplist=list()
			for k in range(len(files_list)):
				entry=files_list[k]
				fplist.append(entry[0])
			for i in range(len(files_list)):
				entry=files_list[i]
				cnmtfile=entry[0]
				if cnmtfile.endswith('.cnmt.nca'):
					f=squirrelNSP(filepath)
					titleid,titleversion,base_ID,keygeneration,rightsId,RSV,RGV,ctype,metasdkversion,exesdkversion,hasHtmlManual,Installedsize,DeltaSize,ncadata=f.get_data_from_cnmt(cnmtfile)
					for j in range(len(ncadata)):
						row=ncadata[j]
						# print(row)
						if row['NCAtype']!='Meta':
							test1=str(row['NcaId'])+'.nca';test2=str(row['NcaId'])+'.ncz'
							if test1 in fplist or test2 in fplist:
								# print(str(row['NcaId'])+'.nca')
								files.append(str(row['NcaId'])+'.nca')
								filesizes.append(int(row['Size']))	
								sz+=int(row['Size'])								
						elif row['NCAtype']=='Meta':
							# print(str(row['NcaId'])+'.cnmt.nca')
							files.append(str(row['NcaId'])+'.cnmt.nca')
							filesizes.append(int(row['Size']))
							sz+=int(row['Size'])	
			try:
				sec_hashlist=list()	
				# print(files)
				for file in files:
					sha,size,gamecard=f.file_hash(file)
					# print(sha)
					if sha != False:
						sec_hashlist.append(sha)	
			except BaseException as e:
				Print.error('Exception: ' + str(e))											
			f.flush()
			f.close()	
			xci_header,game_info,sig_padding,xci_certificate,root_header,upd_header,norm_header,sec_header,rootSize,upd_multiplier,norm_multiplier,sec_multiplier=sq_tools.get_xciheader(files,filesizes,sec_hashlist)	
			outheader=xci_header
			outheader+=game_info
			outheader+=sig_padding
			outheader+=xci_certificate
			outheader+=root_header
			outheader+=upd_header
			outheader+=norm_header
			outheader+=sec_header	
	properheadsize=len(outheader)
	return outheader,properheadsize,keygeneration,sz,files,total_list
	
def transfer_xci_csv(filepath,destiny="SD",cachefolder=None,override=False,keypatch=False):
	check_connection()
	if destiny=="SD":
		destiny="1: External SD Card\\"
	if cachefolder==None:
		cachefolder=os.path.join(ztools_dir, '_mtp_cache_')	
	print(f"Creating xci for {filepath}")
	xciname=gen_xci_parts(filepath,cachefolder=cachefolder,keypatch=keypatch)
	destinypath=os.path.join(destiny,xciname)	
	files_csv=os.path.join(cachefolder, 'files.csv')	
	process=subprocess.Popen([nscb_mtp,"TransferfromCSV","-cs",files_csv,"-dst",destinypath])		
	while process.poll()==None:
		if process.poll()!=None:
			process.terminate();	
	if os.path.exists(cachefolder):			
		for f in os.listdir(cachefolder):
			fp = os.path.join(cachefolder, f)
			try:
				shutil.rmtree(fp)
			except OSError:
				os.remove(fp)		
	
def gen_xci_parts(filepath,cachefolder=None,keypatch=False):
	if keypatch!=False:
		try:
			keypatch=int(keypatch)
		except:	keypatch=False
	if cachefolder==None:
		cachefolder=os.path.join(ztools_dir, '_mtp_cache_')	
	if not os.path.exists(cachefolder):
		os.makedirs(cachefolder)
	else:
		for f in os.listdir(cachefolder):
			fp = os.path.join(cachefolder, f)
			try:
				shutil.rmtree(fp)
			except OSError:
				os.remove(fp)
	outheader,properheadsize,keygeneration,sz,files,files_list=get_header_size([filepath])
	properheadsize=len(outheader)
	# print(properheadsize)
	# print(bucketsize)
	i=0;sum=properheadsize;
	if filepath.endswith('xci'):
		xci=squirrelXCI(filepath)
		outfile=os.path.join(cachefolder, "0")
		outf = open(outfile, 'w+b')		
		outf.write(outheader)	
		written=0
		for fi in files:
			for nspF in xci.hfs0:	
				if str(nspF._path)=="secure":
					for nca in nspF:					
						if nca._path==fi:
							nca=Nca(nca)
							crypto1=nca.header.getCryptoType()
							crypto2=nca.header.getCryptoType2()	
							if crypto2>crypto1:
								masterKeyRev=crypto2
							if crypto2<=crypto1:	
								masterKeyRev=crypto1									
							crypto = aes128.AESECB(Keys.keyAreaKey(Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex))
							hcrypto = aes128.AESXTS(uhx(Keys.get('header_key')))	
							gc_flag='00'*0x01					
							crypto1=nca.header.getCryptoType()
							crypto2=nca.header.getCryptoType2()					
							if nca.header.getRightsId() != 0:					
								nca.rewind()	
								if crypto2>crypto1:
									masterKeyRev=crypto2
								if crypto2<=crypto1:	
									masterKeyRev=crypto1	
								from mtp_tools import get_nca_ticket
								check,titleKey=get_nca_ticket(filepath,fi)
								if check==False:
									sys.exit("Can't verify titleckey")
								titleKeyDec = Keys.decryptTitleKey(titleKey, Keys.getMasterKeyIndex(int(masterKeyRev)))							
								encKeyBlock = crypto.encrypt(titleKeyDec * 4)
								if str(keypatch) != "False":
									t = tqdm(total=False, unit='B', unit_scale=False, leave=False)	
									if keypatch < nca.header.getCryptoType2():
										encKeyBlock,crypto1,crypto2=squirrelXCI.get_new_cryptoblock(squirrelXCI,nca,keypatch,encKeyBlock,t)	
									t.close()
							if nca.header.getRightsId() == 0:
								nca.rewind()											
								encKeyBlock = nca.header.getKeyBlock()	
								if str(keypatch) != "False":
									t = tqdm(total=False, unit='B', unit_scale=False, leave=False)								
									if keypatch < nca.header.getCryptoType2():
										encKeyBlock,crypto1,crypto2=squirrelXCI.get_new_cryptoblock(squirrelXCI,nca,keypatch,encKeyBlock,t)	
									t.close()									
							nca.rewind()					
							i=0				
							newheader=xci.get_newheader(nca,encKeyBlock,crypto1,crypto2,hcrypto,gc_flag)	
							outf.write(newheader)
							written+=len(newheader)
							nca.seek(0xC00)	
							break					
						else:pass					
		xci.flush()
		xci.close()		
	elif filepath.endswith('nsp'):		
		nsp=squirrelNSP(filepath)
		outfile=os.path.join(cachefolder, "0")
		outf = open(outfile, 'w+b')		
		outf.write(outheader)	
		written=0	
		for fi in files:				
			for nca in nsp:					
				if nca._path==fi:
					nca=Nca(nca)
					crypto1=nca.header.getCryptoType()
					crypto2=nca.header.getCryptoType2()	
					if crypto2>crypto1:
						masterKeyRev=crypto2
					if crypto2<=crypto1:	
						masterKeyRev=crypto1									
					crypto = aes128.AESECB(Keys.keyAreaKey(Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex))
					hcrypto = aes128.AESXTS(uhx(Keys.get('header_key')))	
					gc_flag='00'*0x01					
					crypto1=nca.header.getCryptoType()
					crypto2=nca.header.getCryptoType2()					
					if nca.header.getRightsId() != 0:					
						nca.rewind()	
						if crypto2>crypto1:
							masterKeyRev=crypto2
						if crypto2<=crypto1:	
							masterKeyRev=crypto1		
						from mtp_tools import get_nca_ticket
						check,titleKey=get_nca_ticket(filepath,fi)
						if check==False:
							sys.exit("Can't verify titleckey")							
						titleKeyDec = Keys.decryptTitleKey(titleKey, Keys.getMasterKeyIndex(int(masterKeyRev)))							
						encKeyBlock = crypto.encrypt(titleKeyDec * 4)
						if str(keypatch) != "False":
							t = tqdm(total=False, unit='B', unit_scale=False, leave=False)	
							if keypatch < nca.header.getCryptoType2():
								encKeyBlock,crypto1,crypto2=squirrelNSP.get_new_cryptoblock(squirrelNSP,nca,keypatch,encKeyBlock,t)	
							t.close()
					if nca.header.getRightsId() == 0:
						nca.rewind()											
						encKeyBlock = nca.header.getKeyBlock()	
						if str(keypatch) != "False":
							t = tqdm(total=False, unit='B', unit_scale=False, leave=False)								
							if keypatch < nca.header.getCryptoType2():
								encKeyBlock,crypto1,crypto2=squirrelNSP.get_new_cryptoblock(squirrelNSP,nca,keypatch,encKeyBlock,t)	
							t.close()									
					nca.rewind()					
					i=0				
					newheader=nsp.get_newheader(nca,encKeyBlock,crypto1,crypto2,hcrypto,gc_flag)	
					outf.write(newheader)
					written+=len(newheader)
					nca.seek(0xC00)	
					break					
				else:pass					
		nsp.flush()
		nsp.close()								
	outf.flush()							
	outf.close()		
	tfile=os.path.join(cachefolder, "files.csv")	
	with open(tfile,'w') as csvfile:	
		csvfile.write("{}|{}|{}|{}|{}|{}\n".format("step","filepath","size","targetsize","off1","off2"))	
		csvfile.write("{}|{}|{}|{}|{}|{}\n".format(0,outfile,properheadsize+written,properheadsize,0,properheadsize))	
		k=0;l=0		
		for fi in files:
			for j in files_list:
				if j[0]==fi:	
					csvfile.write("{}|{}|{}|{}|{}|{}\n".format(k+1,outfile,properheadsize+written,0xC00,(properheadsize+l*0xC00),(properheadsize+(l*0xC00)+0xC00)))	
					off1=j[1]+0xC00
					off2=j[2]
					targetsize=j[3]-0xC00				
					csvfile.write("{}|{}|{}|{}|{}|{}\n".format(k+2,filepath,(os.path.getsize(filepath)),targetsize,off1,off2))	
					break
			k+=2;l+=1	
	xciname="test.xci"				
	try:
		g=os.path.basename(filepath) 				
		xciname=g[:-3]+'xci'
	except:pass
	return xciname					

def transfer_mxci_csv(tfile=None,destiny="SD",cachefolder=None,override=False,keypatch=False,input_files=None):
	check_connection()
	if input_files==None and tfile==None:
		sys.exit("Missing input!!!")
	if destiny=="SD":
		destiny="1: External SD Card\\"
	if cachefolder==None:
		cachefolder=os.path.join(ztools_dir, '_mtp_cache_')	
	if input_files==None:	
		input_files=listmanager.read_lines_to_list(tfile,all=True)
	print(f"Creating mxci from {tfile}")
	xciname=gen_mxci_parts(input_files,cachefolder=cachefolder,keypatch=keypatch)
	destinypath=os.path.join(destiny,xciname)	
	files_csv=os.path.join(cachefolder, 'files.csv')	
	process=subprocess.Popen([nscb_mtp,"TransferfromCSV","-cs",files_csv,"-dst",destinypath])		
	while process.poll()==None:
		if process.poll()!=None:
			process.terminate();	
	if os.path.exists(cachefolder):			
		for f in os.listdir(cachefolder):
			fp = os.path.join(cachefolder, f)
			try:
				shutil.rmtree(fp)
			except OSError:
				os.remove(fp)	
				
def gen_multi_file_header(prlist,filelist):
	oflist=[];osizelist=[];ototlist=[];files=[]
	totSize=0
	for i in range(len(prlist)):
		for j in prlist[i][4]:
			el=j[0]
			if el.endswith('.nca'):
				oflist.append(j[0])
				#print(j[0])
				totSize = totSize+j[1]
				#print(j[1])
			ototlist.append(j[0])
	sec_hashlist=list()
	GClist=list()
	# print(filelist)
	for file in oflist:
		for filepath in filelist:
			if filepath.endswith('.nsp') or filepath.endswith('.nsz'):
				try:
					f = squirrelNSP(filepath)
					sha,size,gamecard=f.file_hash(file)
					if sha != False:
						sec_hashlist.append(sha)
						osizelist.append(size)
						GClist.append([file,gamecard])
					f.flush()
					f.close()
				except BaseException as e:
					Print.error('Exception: ' + str(e))
			if filepath.endswith('.xci') or filepath.endswith('.xcz'):
				try:
					f = squirrelXCI(filepath)		
					sha,size,gamecard=f.file_hash(file)
					if sha != False:
						sec_hashlist.append(sha)
						osizelist.append(size)
						GClist.append([file,gamecard])
					f.flush()
					f.close()
				except BaseException as e:
					Print.error('Exception: ' + str(e))
	xci_header,game_info,sig_padding,xci_certificate,root_header,upd_header,norm_header,sec_header,rootSize,upd_multiplier,norm_multiplier,sec_multiplier=sq_tools.get_xciheader(oflist,osizelist,sec_hashlist)
	totSize=len(xci_header)+len(game_info)+len(sig_padding)+len(xci_certificate)+rootSize
	outheader=xci_header
	outheader+=game_info
	outheader+=sig_padding
	outheader+=xci_certificate
	outheader+=root_header
	outheader+=upd_header
	outheader+=norm_header
	outheader+=sec_header	
	properheadsize=len(outheader)
	return outheader,properheadsize,totSize,oflist								

def gen_mxci_parts(input_files,cachefolder=None,keypatch=False):
	from listmanager import calculate_name
	if keypatch!=False:
		try:
			keypatch=int(keypatch)
		except:	keypatch=False
	if cachefolder==None:
		cachefolder=os.path.join(ztools_dir, '_mtp_cache_')	
	if not os.path.exists(cachefolder):
		os.makedirs(cachefolder)
	else:
		for f in os.listdir(cachefolder):
			fp = os.path.join(cachefolder, f)
			try:
				shutil.rmtree(fp)
			except OSError:
				os.remove(fp)
	end_name,prlist=calculate_name(input_files,romanize=True,ext='.xci')
	print(f"Calculated name {end_name}")
	outheader,properheadsize,sz,files=gen_multi_file_header(prlist,input_files)
	properheadsize=len(outheader)
	outfile=os.path.join(cachefolder, "0")
	outf = open(outfile, 'w+b')		
	outf.write(outheader)		
	# print(properheadsize)
	# print(bucketsize)
	i=0;sum=properheadsize;
	for fi in files:
		for filepath in input_files:
			if filepath.endswith('xci'):
				xci=squirrelXCI(filepath)
				written=0	
				for nspF in xci.hfs0:	
					if str(nspF._path)=="secure":
						for nca in nspF:					
							if nca._path==fi:
								nca=Nca(nca)
								crypto1=nca.header.getCryptoType()
								crypto2=nca.header.getCryptoType2()	
								if crypto2>crypto1:
									masterKeyRev=crypto2
								if crypto2<=crypto1:	
									masterKeyRev=crypto1									
								crypto = aes128.AESECB(Keys.keyAreaKey(Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex))
								hcrypto = aes128.AESXTS(uhx(Keys.get('header_key')))	
								gc_flag='00'*0x01					
								crypto1=nca.header.getCryptoType()
								crypto2=nca.header.getCryptoType2()					
								if nca.header.getRightsId() != 0:					
									nca.rewind()	
									if crypto2>crypto1:
										masterKeyRev=crypto2
									if crypto2<=crypto1:	
										masterKeyRev=crypto1
									from mtp_tools import get_nca_ticket
									check,titleKey=get_nca_ticket(filepath,fi)
									if check==False:
										sys.exit("Can't verify titleckey")
									titleKeyDec = Keys.decryptTitleKey(titleKey, Keys.getMasterKeyIndex(int(masterKeyRev)))							
									encKeyBlock = crypto.encrypt(titleKeyDec * 4)
									if str(keypatch) != "False":
										t = tqdm(total=False, unit='B', unit_scale=False, leave=False)	
										if keypatch < nca.header.getCryptoType2():
											encKeyBlock,crypto1,crypto2=squirrelXCI.get_new_cryptoblock(squirrelXCI,nca,keypatch,encKeyBlock,t)	
										t.close()
								if nca.header.getRightsId() == 0:
									nca.rewind()											
									encKeyBlock = nca.header.getKeyBlock()	
									if str(keypatch) != "False":
										t = tqdm(total=False, unit='B', unit_scale=False, leave=False)								
										if keypatch < nca.header.getCryptoType2():
											encKeyBlock,crypto1,crypto2=squirrelXCI.get_new_cryptoblock(squirrelXCI,nca,keypatch,encKeyBlock,t)	
										t.close()									
								nca.rewind()					
								i=0				
								newheader=xci.get_newheader(nca,encKeyBlock,crypto1,crypto2,hcrypto,gc_flag)	
								outf.write(newheader)
								written+=len(newheader)
								nca.seek(0xC00)	
								break					
							else:pass					
				xci.flush()
				xci.close()		
			elif filepath.endswith('nsp'):		
				nsp=squirrelNSP(filepath)
				written=0				
				for nca in nsp:					
					if nca._path==fi:
						nca=Nca(nca)
						crypto1=nca.header.getCryptoType()
						crypto2=nca.header.getCryptoType2()	
						if crypto2>crypto1:
							masterKeyRev=crypto2
						if crypto2<=crypto1:	
							masterKeyRev=crypto1									
						crypto = aes128.AESECB(Keys.keyAreaKey(Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex))
						hcrypto = aes128.AESXTS(uhx(Keys.get('header_key')))	
						gc_flag='00'*0x01					
						crypto1=nca.header.getCryptoType()
						crypto2=nca.header.getCryptoType2()					
						if nca.header.getRightsId() != 0:					
							nca.rewind()	
							if crypto2>crypto1:
								masterKeyRev=crypto2
							if crypto2<=crypto1:	
								masterKeyRev=crypto1		
							from mtp_tools import get_nca_ticket
							check,titleKey=get_nca_ticket(filepath,fi)
							if check==False:
								sys.exit("Can't verify titleckey")
							titleKeyDec = Keys.decryptTitleKey(titleKey, Keys.getMasterKeyIndex(int(masterKeyRev)))							
							encKeyBlock = crypto.encrypt(titleKeyDec * 4)
							if str(keypatch) != "False":
								t = tqdm(total=False, unit='B', unit_scale=False, leave=False)	
								if keypatch < nca.header.getCryptoType2():
									encKeyBlock,crypto1,crypto2=squirrelNSP.get_new_cryptoblock(squirrelNSP,nca,keypatch,encKeyBlock,t)	
								t.close()
						if nca.header.getRightsId() == 0:
							nca.rewind()											
							encKeyBlock = nca.header.getKeyBlock()	
							if str(keypatch) != "False":
								t = tqdm(total=False, unit='B', unit_scale=False, leave=False)								
								if keypatch < nca.header.getCryptoType2():
									encKeyBlock,crypto1,crypto2=squirrelNSP.get_new_cryptoblock(squirrelNSP,nca,keypatch,encKeyBlock,t)	
								t.close()									
						nca.rewind()					
						i=0				
						newheader=nsp.get_newheader(nca,encKeyBlock,crypto1,crypto2,hcrypto,gc_flag)	
						outf.write(newheader)
						written+=len(newheader)
						nca.seek(0xC00)	
						break					
					else:pass					
				nsp.flush()
				nsp.close()								
	outf.flush()							
	outf.close()		
	tfile=os.path.join(cachefolder, "files.csv")	
	with open(tfile,'w') as csvfile:	
		csvfile.write("{}|{}|{}|{}|{}|{}\n".format("step","filepath","size","targetsize","off1","off2"))	
		csvfile.write("{}|{}|{}|{}|{}|{}\n".format(0,outfile,properheadsize+written,properheadsize,0,properheadsize))	
		k=0;l=0		
		for fi in files:		
			for filepath in input_files:
				if filepath.endswith('xci'):
					files_list=sq_tools.ret_xci_offsets(filepath)			
				elif filepath.endswith('nsp'):
					files_list=sq_tools.ret_nsp_offsets(filepath)
				for j in files_list:
					if j[0]==fi:	
						csvfile.write("{}|{}|{}|{}|{}|{}\n".format(k+1,outfile,properheadsize+written,0xC00,(properheadsize+l*0xC00),(properheadsize+(l*0xC00)+0xC00)))	
						off1=j[1]+0xC00
						off2=j[2]
						targetsize=j[3]-0xC00				
						csvfile.write("{}|{}|{}|{}|{}|{}\n".format(k+2,filepath,(os.path.getsize(filepath)),targetsize,off1,off2))	
						break
			k+=2;l+=1		
	return end_name					
				