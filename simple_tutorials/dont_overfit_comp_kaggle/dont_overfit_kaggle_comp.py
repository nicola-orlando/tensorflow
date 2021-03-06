# This is a simple script to build a ML model based on Decisionn Trees to be used for the competition 
# https://www.kaggle.com/c/dont-overfit-ii/data. It is largely based on this other script 
# https://github.com/nicola-orlando/tensorflow/blob/master/simple_tutorials/low_statistics_classification.py
# Class in TensorFlow https://www.tensorflow.org/api_docs/python/tf/estimator/BoostedTreesClassifier 
# [1] https://www.tensorflow.org/tensorboard/hyperparameter_tuning_with_hparams
# [2] https://www.tensorflow.org/datasets/splits
# [3] https://stackoverflow.com/questions/40729162/merging-results-from-model-predict-with-original-pandas-dataframe

from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np
import uproot
import tensorflow as tf
tf.enable_eager_execution()
tf.logging.set_verbosity(tf.logging.ERROR)
tf.set_random_seed(123)

from keras.layers import Input, Flatten, Dense, Dropout
from keras.models import Model
from scipy.stats import uniform
from collections import Counter

import pandas as pd
 
from sklearn.model_selection import RandomizedSearchCV
from sklearn import linear_model
from sklearn.linear_model import LogisticRegression
from sklearn import svm
from sklearn.svm import LinearSVC
from sklearn import linear_model
from sklearn.ensemble import AdaBoostClassifier
from sklearn import tree
from sklearn.tree import DecisionTreeClassifier

from sklearn.model_selection import RepeatedKFold

import pickle

# Remove verbose warnings 
from warnings import simplefilter
simplefilter(action='ignore', category=FutureWarning)
simplefilter(action='ignore', category=DeprecationWarning)

# Configuration of the job, to be parsed from command line eventually
number_of_folds=3
is_verbose=False 

# PART 1 design the dataset handling for 10-fold cross training
# Now it's time to run, before then, split the dataset accroding to the cross training granularity we want to use 
# See Ref [2]

# My data after downloading will be here /afs/cern.ch/user/o/orlando/.keras/datasets/
# For now hard coded grabbing 
# Data header: id,target,features[0-299]
print("Load the dataset ...")
train_file_path = "/afs/cern.ch/user/o/orlando/.keras/datasets/dont-overfit-ii/train.csv"
dftrain_original = pd.read_csv(train_file_path)
# Dropping from the dataset the uninteresting index
dftrain = dftrain_original.drop('id', 1)

# Look at the dataset structure
print("Looking at the input data ...")
print(dftrain.head())
print(dftrain.describe())

# PART 2 design the functions used to handle the HP scan and run functionalites

# For saving the model
def save_model(name,model):
  pickle.dump(model, open(name, 'wb'))
  
# Train a logistic regression model performing an HP scan, print the best found HP set and return a model having the best found HP setting 
def train_validate_model_logreg(X_train,y_train,X_test,y_test,full_dataframe,fold_number,print_verbose=False):
  print("Training a Logistic Regression model")
  logistic = LogisticRegression(solver='saga', tol=0.01, max_iter=200,random_state=0)
  #Some HP combinations not necessarily available
  hp_setting = dict(tol=uniform(loc=0, scale=3),
                    penalty=['l2', 'l1'],
                    C=uniform(loc=0, scale=4),
                    fit_intercept=[True,False],
                    solver=['liblinear', 'saga'],
                    max_iter=uniform(loc=50, scale=200) )
  clf = RandomizedSearchCV(logistic,hp_setting,random_state=0)
  search = clf.fit(X_train,y_train)
  scores_train_prediction=search.predict(X_train)
  save_model('logreg_fold_'+fold_number+'.pkl',clf.best_estimator_)
  if print_verbose :
    print('Best hp setting')
    print(search.best_params_)
    print('Printing predictions')
    print(scores_train_predictions)
    print('Printing random search results')
    print(search.cv_results_)
  score_predictions = search.predict(X_test)
  dataframe_with_scores = pd.DataFrame(data = score_predictions, columns = ['score_predictions_logistic'], index = X_test.index.copy())
  output_dataframe = pd.merge(full_dataframe, dataframe_with_scores, how = 'left', left_index = True, right_index = True)
  return output_dataframe

def train_validate_model_svm(X_train,y_train,X_test,y_test,full_dataframe,fold_number,kernel='linear',print_verbose=False):
    print("Training a SVM model")
    svm_class = 0
    if kernel == 'linear': 
      svm_class = LinearSVC(random_state=0, tol=1e-5)
    else:
      svm_class = svm.SVC(kernel=kernel)
    # HP setting 
    hp_setting = 0
    if kernel == 'linear':
      hp_setting = dict(penalty=['l2'],
                        loss=['hinge', 'squared_hinge'],
                        dual=[True],
                        tol=uniform(loc=0, scale=3),
                        C=uniform(loc=0, scale=4),
                        fit_intercept=[True, False],
                        intercept_scaling=uniform(loc=0, scale=3),
                        max_iter=uniform(loc=50, scale=200))
    else : 
      hp_setting = dict(C=uniform(loc=0, scale=4),
                        degree=[1,2],
                        coef0=uniform(loc=0,scale=10))
    clf = RandomizedSearchCV(svm_class,hp_setting,random_state=0)
    search = clf.fit(X_train,y_train)
    scores_train_predictions=search.predict(X_train)
    save_model('svm_'+kernel+'_fold_'+fold_number+'.pkl',clf.best_estimator_)
    if print_verbose :
      print('Best hp setting')
      print(search.best_params_)
      print('Printing predictions')
      print(scores_train_predictions)
      print('Printing random search results')
      print(search.cv_results_)
    score_predictions = search.predict(X_test)
    dataframe_with_scores = pd.DataFrame(data = score_predictions, columns = ['score_predictions_svm_'+kernel], index = X_test.index.copy())
    output_dataframe = pd.merge(full_dataframe, dataframe_with_scores, how = 'left', left_index = True, right_index = True)
    return output_dataframe

def train_bayesian_rdge(X_train,y_train,X_test,y_test,full_dataframe,fold_number,print_verbose=False):
  print("Training a Bayesian model")
  bayesian_model = linear_model.BayesianRidge()
  bayesian_model.fit(X_train,y_train)
  score_predictions_train = bayesian_model.predict(X_train)
  score_predictions = bayesian_model.predict(X_test)
  save_model('bayesian_model_fold_'+fold_number+'.pkl',bayesian_model)
  if print_verbose: 
    print('Print score_predictions_train')
    print(score_predictions_train)
    print('Print score_predictions')
    print(score_predictions)
  dataframe_with_scores = pd.DataFrame(data = score_predictions, columns = ['score_predictions_bayes'], index = X_test.index.copy())
  output_dataframe = pd.merge(full_dataframe, dataframe_with_scores, how = 'left', left_index = True, right_index = True)
  return output_dataframe

# https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeClassifier.html#sklearn.tree.DecisionTreeClassifier
def train_validate_model_decision_tree(X_train,y_train,X_test,y_test,full_dataframe,fold_number,print_verbose=False):
  print("Training a DecisionTree model")
  # max_features currently set to None, can inspect this a little further   
  decision_tree = tree.DecisionTreeClassifier()
  # HP setting 
  hp_setting = dict(criterion=['gini','entropy'], 
                    splitter=['best','random'], 
                    max_depth=[None,1,2,3,4], 
                    min_samples_split=uniform(loc=0, scale=0.15),
                    min_samples_leaf=uniform(loc=0, scale=0.1),
                    max_leaf_nodes=[None,10,20,30,40,50,60,70,80,90,100]) 
  clf = RandomizedSearchCV(decision_tree,hp_setting,random_state=0)
  search = clf.fit(X_train,y_train)
  scores_train_prediction=search.predict(X_train)
  save_model('bdt_fold_'+fold_number+'.pkl',clf.best_estimator_)
  if print_verbose :
    print('Best hp setting')
    print(search.best_params_)
    print('Printing predictions')
    print(scores_train_prediction)
    print('Printing random search results')
    print(search.cv_results_)
  score_predictions = search.predict(X_test)
  dataframe_with_scores = pd.DataFrame(data = score_predictions, columns = ['score_predictions_decision_tree'], index = X_test.index.copy())
  output_dataframe = pd.merge(full_dataframe, dataframe_with_scores, how = 'left', left_index = True, right_index = True)
  return output_dataframe

def train_validate_model_lasso(X_train,y_train,X_test,y_test,full_dataframe,fold_number,print_verbose=False):
  print("Training a Lasso model")
  lasso_model = linear_model.Lasso()
  hp_setting = dict(alpha=uniform(loc=0.001, scale=0.999))
  clf = RandomizedSearchCV(lasso_model,hp_setting,random_state=0)
  search = clf.fit(X_train,y_train)
  scores_train_prediction=search.predict(X_train)
  save_model('lasso_fold_'+fold_number+'.pkl',clf.best_estimator_)
  if print_verbose :
    print('Best hp setting')
    print(search.best_params_)
    print('Printing predictions')
    print(scores_train_prediction)
    print('Printing random search results')
    print(search.cv_results_)
  score_predictions = search.predict(X_test)
  dataframe_with_scores = pd.DataFrame(data = score_predictions, columns = ['score_predictions_lasso'], index = X_test.index.copy())
  output_dataframe = pd.merge(full_dataframe, dataframe_with_scores, how = 'left', left_index = True, right_index = True)
  return output_dataframe

# Now we need to split the data, and call the runner for training/evaluating the model from the splitting look  
X = dftrain.to_numpy()

random_state = 12883823
# See documentation here https://scikit-learn.org/stable/modules/cross_validation.html
# Here for the predict function https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_predict.html#sklearn.model_selection.cross_val_predict

fold_count=0
dataframes_with_logreg_scores=[]
dataframes_with_svm_linear_scores=[]
dataframes_with_svm_pol_scores=[]
dataframes_with_lasso_scores=[]
dataframes_with_decision_tree_scores=[]
dataframes_with_bayes_scores=[]

repeated_k_fold = RepeatedKFold(n_splits=number_of_folds, n_repeats=1, random_state=random_state)

for train_index, test_index in repeated_k_fold.split(X):
  fold_count+=1
  print("Processing fold count ",fold_count)

  # Converting to dataframe
  # values, 1st column as index
  dataframe_from_numpy_train = pd.DataFrame(dftrain,index=train_index,columns=list(dftrain.columns.values))
  dataframe_from_numpy_test = pd.DataFrame(dftrain,index=test_index,columns=list(dftrain.columns.values))
  
  # Pickup the target column 
  y_train = dataframe_from_numpy_train.pop('target')
  y_test = dataframe_from_numpy_test.pop('target')

  print('Count the data split by class')
  print(Counter(y_test))
 
  dataframe_with_logreg_scores = train_validate_model_logreg(dataframe_from_numpy_train,y_train,dataframe_from_numpy_test,y_test,dftrain,str(fold_count))
  dataframe_with_svm_linear_scores = train_validate_model_svm(dataframe_from_numpy_train,y_train,dataframe_from_numpy_test,y_test,dftrain,str(fold_count),'linear')
  dataframe_with_svm_pol_scores = train_validate_model_svm(dataframe_from_numpy_train,y_train,dataframe_from_numpy_test,y_test,dftrain,str(fold_count),'poly')
  dataframe_with_lasso_scores = train_validate_model_lasso(dataframe_from_numpy_train,y_train,dataframe_from_numpy_test,y_test,dftrain,str(fold_count))
  dataframe_with_decision_tree_scores = train_validate_model_decision_tree(dataframe_from_numpy_train,y_train,dataframe_from_numpy_test,y_test,dftrain,str(fold_count))
  dataframe_with_bayes_scores = train_bayesian_rdge(dataframe_from_numpy_train,y_train,dataframe_from_numpy_test,y_test,dftrain,str(fold_count))

  dataframes_with_logreg_scores.append(dataframe_with_logreg_scores)
  dataframes_with_svm_linear_scores.append(dataframe_with_svm_linear_scores)
  dataframes_with_svm_pol_scores.append(dataframe_with_svm_pol_scores)
  dataframes_with_lasso_scores.append(dataframe_with_lasso_scores)
  dataframes_with_decision_tree_scores.append(dataframe_with_decision_tree_scores)
  dataframes_with_bayes_scores.append(dataframe_with_bayes_scores)

combined_dataframe_with_logreg_scores = dataframes_with_logreg_scores[0]
combined_dataframe_with_svm_linear_scores = dataframes_with_svm_linear_scores[0]
combined_dataframe_with_svm_pol_scores = dataframes_with_svm_pol_scores[0]
combined_dataframe_with_lasso_scores = dataframes_with_lasso_scores[0]
combined_dataframe_with_decision_tree_scores = dataframes_with_decision_tree_scores[0]
combined_dataframe_with_bayes_scores = dataframes_with_bayes_scores[0]

for element in range(0,number_of_folds-1):
    combined_dataframe_with_logreg_scores['score_predictions_logistic'] = combined_dataframe_with_logreg_scores['score_predictions_logistic'].combine_first(dataframes_with_logreg_scores[element+1]['score_predictions_logistic'])
    combined_dataframe_with_svm_linear_scores['score_predictions_svm_linear'] = combined_dataframe_with_svm_linear_scores['score_predictions_svm_linear'].combine_first(dataframes_with_svm_linear_scores[element+1]['score_predictions_svm_linear'])
    combined_dataframe_with_svm_pol_scores['score_predictions_svm_poly'] = combined_dataframe_with_svm_pol_scores['score_predictions_svm_poly'].combine_first(dataframes_with_svm_pol_scores[element+1]['score_predictions_svm_poly'])
    combined_dataframe_with_lasso_scores['score_predictions_lasso'] = combined_dataframe_with_lasso_scores['score_predictions_lasso'].combine_first(dataframes_with_lasso_scores[element+1]['score_predictions_lasso'])
    combined_dataframe_with_decision_tree_scores['score_predictions_decision_tree'] = combined_dataframe_with_decision_tree_scores['score_predictions_decision_tree'].combine_first(dataframes_with_decision_tree_scores[element+1]['score_predictions_decision_tree'])
    combined_dataframe_with_bayes_scores['score_predictions_bayes'] = combined_dataframe_with_bayes_scores['score_predictions_bayes'].combine_first(dataframes_with_bayes_scores[element+1]['score_predictions_bayes'])

if is_verbose: 
  print('Printing final dataframe')
  print(combined_dataframe_with_logreg_scores.head())
  print(combined_dataframe_with_svm_linear_scores.head())
  print(combined_dataframe_with_svm_pol_scores.head())
  print(combined_dataframe_with_lasso_scores.head())
  print(combined_dataframe_with_decision_tree_scores.head())
  print(combined_dataframe_with_bayes_scores.head())

# Print out the dataframe for investigation
combined_dataframe_with_logreg_scores.to_csv('log_out_final_dataset.csv', index=False) 
combined_dataframe_with_svm_linear_scores.to_csv('svm_linear_out_final_dataset.csv', index=False) 
combined_dataframe_with_svm_pol_scores.to_csv('svm_pol_out_final_dataset.csv', index=False) 
combined_dataframe_with_lasso_scores.to_csv('lasso_out_final_dataset.csv', index=False) 
combined_dataframe_with_decision_tree_scores.to_csv('decision_tree_out_final_dataset.csv', index=False) 
combined_dataframe_with_bayes_scores.to_csv('bayes_out_final_dataset.csv', index=False) 

matching_labels_logistic = combined_dataframe_with_logreg_scores[combined_dataframe_with_logreg_scores.target == combined_dataframe_with_logreg_scores.score_predictions_logistic]
matching_labels_svm_linear = combined_dataframe_with_svm_linear_scores[combined_dataframe_with_svm_linear_scores.target == combined_dataframe_with_svm_linear_scores.score_predictions_svm_linear]
matching_labels_svm_pol = combined_dataframe_with_svm_pol_scores[combined_dataframe_with_svm_pol_scores.target == combined_dataframe_with_svm_pol_scores.score_predictions_svm_poly]
matching_labels_lasso = combined_dataframe_with_lasso_scores[combined_dataframe_with_lasso_scores.target == combined_dataframe_with_lasso_scores.score_predictions_lasso]
matching_labels_decision_tree = combined_dataframe_with_decision_tree_scores[combined_dataframe_with_decision_tree_scores.target == combined_dataframe_with_decision_tree_scores.score_predictions_decision_tree]

if is_verbose:
  print('Dataset component with matching labels to predictions')
  print(matching_labels_logistic.head(-1))
  print(matching_labels_svm_linear.head(-1))
  print(matching_labels_svm_pol.head(-1))
  print(matching_labels_lasso.head(-1))
  print(matching_labels_decision_tree.head(-1))

dftrain_original['score_predictions_logistic'] = combined_dataframe_with_logreg_scores['score_predictions_logistic'] 
dftrain_original['score_predictions_svm_linear'] = combined_dataframe_with_svm_linear_scores['score_predictions_svm_linear'] 
dftrain_original['score_predictions_svm_poly'] = combined_dataframe_with_svm_pol_scores['score_predictions_svm_poly'] 
dftrain_original['score_predictions_lasso'] = combined_dataframe_with_lasso_scores['score_predictions_lasso'] 
dftrain_original['score_predictions_decision_tree'] = combined_dataframe_with_decision_tree_scores['score_predictions_decision_tree'] 
dftrain_original['score_predictions_bayes'] = combined_dataframe_with_bayes_scores['score_predictions_bayes'] 

# Derive final classifier output based on logistic, linear svm and decision tree model 
dftrain_original['score_final'] = np.where( dftrain_original['score_predictions_logistic']+dftrain_original['score_predictions_svm_linear']+dftrain_original['score_predictions_decision_tree'] >= 2, 1, 0)

print(dftrain_original.head(5))

dftrain_original.to_csv('full_dataset.csv', index=False) 
matching_labels_full = dftrain_original[dftrain_original.target == dftrain_original.score_final]
matching_labels_full.to_csv('full_dataset_matching.csv', index=False) 

# PART 3. Now apply the various models on the testing dataset. Decided to use logreg, bdt and svm with linear kernel 
models_names=['logreg','bdt','svm_linear']
folds=['1','2','3']

test_file_path = "/afs/cern.ch/user/o/orlando/.keras/datasets/dont-overfit-ii/test.csv"
dftest_original = pd.read_csv(test_file_path)
dftest = dftest_original.drop('id', 1)

X_test = pd.DataFrame(dftest,columns=list(dftest.columns.values))

for model in models_names: 
  for fold in folds: 
    print('Processing application model '+model+' fold no '+fold)
    model_name=model+'_fold_'+fold+'.pkl'
    score_name=model_name.split('.')[0]
    loaded_model=pickle.load(open(model_name, 'rb'))
    score = loaded_model.predict(X_test)
    dataframe_with_scores = pd.DataFrame(data=score, columns = ['score_'+score_name], index = X_test.index.copy())
    dftest = pd.merge(dftest, dataframe_with_scores, how = 'left', left_index = True, right_index = True)

dftest_original['score_final'] = np.where(dftest['score_logreg_fold_1'] +
                                 dftest['score_logreg_fold_2'] +
                                 dftest['score_logreg_fold_3'] +
                                 dftest['score_bdt_fold_1'] +
                                 dftest['score_bdt_fold_2'] +
                                 dftest['score_bdt_fold_3'] +
                                 dftest['score_svm_linear_fold_1'] +
                                 dftest['score_svm_linear_fold_2'] +
                                 dftest['score_svm_linear_fold_3'] >= 5, 1, 0)


# Finally remove all features in the training dataset just for the submission 
for feature in range(0,300): 
  dftest_original = dftest_original.drop(str(feature), 1)
print(dftest_original.head(5))
dftest_original.to_csv('submission_file.csv', index=False) 
