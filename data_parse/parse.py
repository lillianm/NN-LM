import re
import sys,os
#symbols = {"%hes":"err","%spk":"well","%int":"%laugh","noise":""}
symbols = {"%hes":"","%spk":"","%int":"","noise":""}
addition = {"--":" "}
# how to use those 


def parse_txt_file (fileName, dirName, mode):
	file1 = open(fileName)
	file2 = open(mode + "_cesar_data.txt.text","a")
	file3 = open(mode + "_cesar_data.txt.feat","a")
	for line in file1:
		line_origin = line
		text = line.split("\t")[-1]
		feat = line.split("\t")[-2]
		# only extract the text part
		pattern = re.compile("[a-zA-Z\s\^'%()\-'<>]+")
		text = re.search(pattern, text)
		if text:
			text = text.group(0)
			# not useful tags 
			noUseTags = re.compile("<//noise>|\n|[()\^\-<>]|noise")
			text = re.sub(noUseTags , "", text)
			# delete space or tab in the beginning of the sentences
			format = re.compile("^\s+")
			for s in symbols:
				text = text.replace(s,symbols.get(s))
				# delete multiple spaces

			text = text.replace("\s{2,}", " ")
			text = re.sub(format, "",text)
			text.replace("%uhhuh","")
			if text:
				file2.write(text+"\n")
				bi_feat = 1;
				if feat=="driver":
					 bi_feat = 1;
				else:
					if feat == "copilot":
						bi_feat = 0;
				file3.write(str(bi_feat)+" "+str(bi_feat)+"\n")

def generate_vocabulary(fileName, mode, vocabulary):
	textFile = open(fileName)
	#vocab = open("vocab_" + mode + ".txt","a")

	for line in textFile:
		pattern = re.compile("[%<>\-/]z|\n")
		nline = re.sub(pattern, "", line)
		nline = nline.replace("\s{2,}"," ")
		words = set(nline.split(" "))
		vocabulary  = vocabulary | words
	return vocabulary

	
def write_vocab(fileName, vocab):
	vocab_file = open(fileName,"w+");
	v = list(vocab)
	v.sort()
	for word in v:
		if word:
			vocab_file.write(word+"\n")

def combine_subset(test_dirName):
	dir = "../CESAR_data"
	fileName = 'data.txt'
	mode = "train";
	train_vocabulary = set([]);
	test_vocabulary = set([]);
	for root, dirs, files in os.walk(dir):
		for subDir in dirs:
			path = os.path.join(dir, subDir)
			if subDir == test_dirName:
				print "testfile"
				mode = "test"
				for r, d, files in os.walk(path):
					if fileName in files:
						print path
						parse_txt_file(os.path.join(path,fileName), subDir,mode)
						test_vocabulary = generate_vocabulary(mode + "_cesar_data.txt.text", mode, test_vocabulary);
			else: 
				mode = "train"
				for r, d, files in os.walk(path):
					if fileName in files:
						print path
						parse_txt_file(os.path.join(path,fileName), subDir,mode)
						train_vocabulary = generate_vocabulary(mode + "_cesar_data.txt.text", mode, train_vocabulary);


	write_vocab("train_vocab.txt",train_vocabulary)
	write_vocab("test_vocab.txt",test_vocabulary)
#main	
#rewrite the previous files
open("train_cesar_data.txt.text","w+")
open("test_cesar_data.txt.text","w+")
open("train_cesar_data.txt.feat","w+")
open("test_cesar_data.txt.feat","w+")
combine_subset("CESAR_May-Tue-29-13-06-47-2012")

# dir = "../CESAR_data"
# fileName = 'data.txt'
# for root, dirs, files in os.walk(dir):
# 	for subDir in dirs:
# 		path = os.path.join(dir, subDir)
# 		for r, d, files in os.walk(path):
# 			if fileName in files:
# 				print fileName
# 				parse_txt_file(os.path.join(path,fileName), subDir)
# 				generate_vocabulary(subDir + "cesar_data.txt.text", subDir)




# file1 = open("data.txt")
# file2 = open("cesar_data.txt.text","w+")
# file3 = open("cesar_data.txt.feat","w+")












