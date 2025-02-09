import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
import streamlit as st
from sklearn.tree import DecisionTreeClassifier

st.markdown("# Robbed or not?")

st.markdown("#### Enter your launch angle and exit velo to see if it should have been a hit or not in D1 baseball")

#load data
bball_df = pd.read_csv("combined_data1.csv")

    #Make the dataset smaller
new_bball = pd.DataFrame({
        "PlayResult" : bball_df["PlayResult"],
        "ExitSpeed" : bball_df["ExitSpeed"],
        "Angle": bball_df["Angle"]
})

    
new_bball["PlayResult"] = np.where(new_bball["PlayResult"] == "Undefined",
                                   np.nan,
                                   new_bball["PlayResult"])
   
new_bball = new_bball.dropna()
    
new_bball = new_bball.copy()  # Ensure we are working with a copy
#create a new row
new_bball.loc[:, "Hit_or_Out"] = new_bball["PlayResult"].apply(lambda x: 1 if x in ["Single", "Double", "Triple", "Homerun"]else 0)

#Select the target categories for the model
y = new_bball["Hit_or_Out"] 
X = new_bball[["ExitSpeed", "Angle"]]

#initalize the model
    
rf_classifier = RandomForestClassifier(n_estimators=30,
                                       max_depth = 7,
                                       min_samples_split = 3,
                                       random_state=206)
    #fit the model on everything because the alg has been trained and tested in different notebook
    
rf_classifier.fit(X, y)
#new data
f1 = st.number_input("What was the exit veocity?", min_value = 1, max_value = 140, value = 88)
f2 = st.number_input("What was the launch angle?", min_value = -100, max_value = 150, value = 12)



newdata = pd.DataFrame({
    "ExitSpeed":[f1],
    "Angle": [f2]})

#Create the function to predict
def predictions (newdata):
    probs = rf_classifier.predict_proba(newdata)
    category = rf_classifier.predict(newdata)
    
    
    return probs, category

#Create a button

if st.button ("Submit data"):
    probs, category = predictions(newdata)
    cat_str = "Hit" if category == 1 else "Out"
    
    st.write (f"The batted ball is should have been a/an {cat_str}!")
    st.write (f" The probability that this batted ball profile is a hit is {round(probs[0][1],2)}.")



    
    

