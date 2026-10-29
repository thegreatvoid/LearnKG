**Sample dataset annotated with Prerequisite Relations according to PREAP (PRErequisite Annotation Protocol)**<p>

The features of the PR-annotated dataset and the options of PREAP adopted in the annotation process are specified in the dataset_metadata file shown in the RDF graph below.

![Metadata describing the sample dataset](https://github.com/IntAIEdu/PRAT/blob/main/data/case-study-annotation/PREAP-sample-CS-dataset/dataset-metadata.png)

CONTENT OF THIS FOLDER

'dataset_metadata.json' & 'dataset_metadata.jpg': JSON-LD & visual RDF graph encoding metadata information about the dataset and the related annotation process (according to Dataset class properties of schema.org vocabulary, based upon W3C DCAT vocabulary).

'rawText.txt': raw text of the textbook chapter used for PR annotation.

'text_linguisticAnalysis.conll': linguistically analysed text (at the morphosyntactic level, i.e. Part-of-Speech and dependency relations) in conll format. The annotation is produced using UDPipe (using pre-trained English model, see https://ufal.mff.cuni.cz/udpipe/1). The tagset is the Universal Dependencies Tagset (for the full tagset and tags meanings, please refer to https://universaldependencies.org/).

'concept_list_automatically_extracted.txt': list of concepts  automatically extracted using T2K (see http://www.italianlp.it/demo/t2k-text-to-knowledge).

'GOLD-PR_Concepts': list of concepts used in the annotation after manual check and revision of the automatically extracted concepts (i.e., autonomous semi-automatic concept annotation).

'GOLD-PR_PairsOnly.tsv': the list of concept pairs marked as PRs during annotation. Note that only manually created pairs are included: non-PRs and transitive pairs are  to be acquired as described in Alzetta et al., 2019, 'Prerequisite or Not Prerequisite? That’s the Problem! An NLP-based Approach for Concept Prerequisites Learning', CLiC-it 2019.

'GOLD-PR_PairsAndContext.tsv': this file contains the list of concept pairs annotated as PRs by the annotators (as above, non-PRs and transitive paris are to be included). Each pair is anchored to the contex where the relation was entered by means of sentence IDs that should be searched for in the file 'text_v2_linguisticAnalysis.conll'.
The present file contains the following informations:
- 'ID': unique identifier of each concept PR pair;
- 'PAIR': concatenation of the terms referring to the prerequsite and target concepts in order to obtain a unique string. Spaces appearing in the concept name are removed and '%' is used to separate the two terms (e.g., prerequisite%target, resulting in 'ACCESS_POINT%GATEWAY').
- 'PREREQUISITE': term referring to the concept appearing in the pair as prerequisite.
- 'TARGET': term referring to the concept appearing in the pair as target.
- 'ID_SENT': unique identifier of the sentence where the relation was entered by the annotator. These IDs refer to the progressive numbering of sentences in the file 'text_v2_linguisticAnalysis.conll'. Example: if ID_SENT=3, it means that the annotator entered the PR relation in the third sentence of the file. Specifically, in the third sentence we can find an occurrence of the target concept that, as described in that context, triggered the presence of a PR pair for the annotator. 
- 'AGREEMENT': number of annotators entering that pair, regardless of the different contexts where the relation was entered.
- 'SENT-1/SENT/SENT+1': these three elements show the window of context where the PR relation was entered. Specifically, in addition to the specific sentence where the PR was annotated  ('SENT'), we report its preceding  ('SENT-1') the following ('SENT+1') sentences.
