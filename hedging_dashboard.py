# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import scipy.stats
import yfinance as yf
#import io
import requests as re
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import quandl
import json
import pickle

@st.cache
def getData():
    
    #url='https://raw.githubusercontent.com/rounder22/cmbs/main/cleaned%20index%20data.csv'
    #s=requests.get(url).content
    #df=pd.read_csv(io.StringIO(s.decode('utf-8')))
    df=pd.read_pickle('index_data.pkl')
    #df=df.set_index('Date').T
    #df.index=pd.to_datetime(df.index)
    df.sort_index(inplace=True)
    
    #TD Ameritrade API
    apiKey='M9YPA8SDNNXYJVWTC3MDQF9ZU8EO93JC'
    customTickers=pickle.load(open('customTickers.pkl','rb'))
    for ticker in customTickers:
        endpoint='https://api.tdameritrade.com/v1//marketdata/%s/pricehistory'%ticker
        data=json.loads(re.get(endpoint,params={'apikey':apiKey,
                                               'periodType':'year',
                                               'period':10,
                                               'frequencyType':'daily',
                                               'frequency':1
                                               }
                              ).content
                        )
        td=pd.DataFrame(data['candles'])
        td['datetime']=pd.to_datetime(td['datetime'],unit='ms')
        td.set_index('datetime',inplace=True)
        td.index=td.index.normalize()
    df=pd.merge(df,td.close,how='outer',left_index=True,right_index=True)
    df.rename(columns={'close':'DXY'},inplace=True)
    
    #Yahoo Data
    yahoo=yf.download(['^GSPC','IVOL','XLF','BAC','JPM','PFIX','NLY','AGNC'],period='5y')
    df=pd.merge(df,yahoo.Close,how='outer',left_index=True,right_index=True)
    df.rename(columns={'^GSPC':'SPX'},inplace=True)
    
    #FRED Data
    api_key='73cf3bed4794ea8277f4d43358d8ce07'
    lsSeries={'UST2Y':'DGS2','UST5Y':'DGS5','UST10Y':'DGS10','UST30Y':'DGS30',
              'Real UST10Y':'DFII10'}
    endpoint='https://api.stlouisfed.org/fred/series/observations'
    for series in lsSeries:
        params={'api_key':api_key,
                'file_type':'json',
                'series_id':lsSeries[series]
                }
        dfFRED=pd.DataFrame(re.get(endpoint,params).json()['observations'])
        dfFRED['value']=dfFRED['value'].str.replace('.','')
        dfFRED['date']=pd.to_datetime(dfFRED['date'])
        dfFRED['value']=pd.to_numeric(dfFRED['value'])
        dfFRED.drop(columns=['realtime_start','realtime_end'],inplace=True)
        dfFRED.rename(columns={'date':'Date'},inplace=True)
        dfFRED.set_index('Date',inplace=True)
        dfFRED.rename(columns={'value':series},inplace=True)
        df=pd.merge(df,dfFRED,how='outer',left_index=True,right_index=True)
    
    #Quandl Data
    quandl.ApiConfig.api_key='56v4NVWgkabqfn_Xy8Rj'
    qData=quandl.get(['LBMA/GOLD','LBMA/SILVER'])
    df=pd.merge(df,qData,how='outer',left_index=True,right_index=True)
    
    return df

def inputData(file):
    df=pd.read_csv(file)
    df=df.dropna().set_index('Date').T
    df.index=pd.to_datetime(df.index)
    
    old=pd.read_pickle('index_data.pkl')
    #old=old.set_index('Date').T
    #old.index=pd.to_datetime(old.index)
    old=old.append(df)
    #old=old[~old.index.duplicated(keep='first')]
    old.to_pickle('index_data.pkl')

##### SIDEBAR #####    
st.sidebar.subheader('Upload Data')
st.sidebar.download_button('Downloand Input Template',
                           data=open('input.csv','rb'),
                           file_name='input.csv'
                           )
file=st.sidebar.file_uploader('Select File',
                              type='csv'
                              )
if st.sidebar.button('Upload'):
    inputData(file)
    
##### MAIN #####    
st.title('Hedging Analysis')
c1,c2=st.columns(2)

#create dataframe for analysis
df=getData()
seriesI=c1.selectbox('Select Independent/Hedge Series',df.columns,index=2)
checkPctI=c1.checkbox('Use Percent Change',key=1)
checkChgI=c1.checkbox('Use Change',key=3)
seriesD=c1.selectbox('Select Dependent/Underlying Series',df.columns,index=7)
checkPctD=c1.checkbox('Use Percent Change',key=2)
checkChgD=c1.checkbox('Use Change',key=4)
df=df[[seriesI,seriesD]].dropna()
dfHR=df[[seriesI,seriesD]].dropna()
#df[seriesI]=pd.to_numeric(df[seriesI],errors='coerce')
#df[seriesD]=pd.to_numeric(df[seriesD],errors='coerce')
#df=df.astype('float').dropna()

if checkPctI:
    df[seriesI]=df[seriesI].pct_change()
    df.dropna(inplace=True)
if checkPctD:
    df[seriesD]=df[seriesD].pct_change()
    df.dropna(inplace=True)
if checkChgI:
    df[seriesI]=df[seriesI].diff()
    df.dropna(inplace=True)
if checkChgD:
    df[seriesD]=df[seriesD].diff()
    df.dropna(inplace=True)    
    
#create stats dataframe
index=['Current Date','Current','Average','StDev','10d StDev','Z-Score']
data=[(df[seriesI].index.max().strftime('%Y-%m-%d'),df[seriesD].index.max().strftime('%Y-%m-%d')),
      (str("{:0.2f}".format(df[seriesI][-1])),str("{:0.2f}".format(df[seriesD][-1]))),
      (str("{:0.2f}".format(df[seriesI].mean())),str("{:0.2f}".format(df[seriesD].mean()))),
      (str("{:0.2f}".format(df[seriesI].std())),str("{:0.2f}".format(df[seriesD].std()))),
      (str("{:0.2f}".format(df[seriesI].rolling(10).std()[-1])),str("{:0.2f}".format(df[seriesD].rolling(10).std()[-1]))),
      (str("{:0.2f}".format((df[seriesI][-1]-df[seriesI].mean())/df[seriesI].std())),
       str("{:0.2f}".format((df[seriesD][-1]-df[seriesD].mean())/df[seriesD].std()))
       ) 
      ]
columns=[seriesI,seriesD]
stats=pd.DataFrame(data=data,index=index,columns=columns)

fig=make_subplots(specs=[[{"secondary_y":True}]])
fig.add_trace(go.Scatter(x=df.index,y=df[seriesI].values,name=seriesI)
              ,secondary_y=False)
fig.add_trace(go.Scatter(x=df.index,y=df[seriesD].values,name=seriesD)
              ,secondary_y=True)
fig.update_xaxes(rangeslider_visible=True,
                 rangeselector=dict(
        buttons=list([
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=3, label="3m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1y", step="year", stepmode="backward"),
            dict(step="all")
        ])
    )
)
c2.write('**Statistics**')
c2.dataframe(stats)
st.plotly_chart(fig)

with st.form('regression'):
    st.subheader('Regession Analysis')
    a,b=st.columns(2)
    firstRegimeCheck=a.checkbox('Use First Regime',
                                value=True,
                                )
    a.markdown('**First Regime**')
    startDate=a.date_input('Start Date',
                            value=df.index.min(),
                            min_value=df.index.min(),
                            max_value=df.index.max(),
                            key=1
                            )
    endDate=a.date_input('End Date',
                          value=df.index.max(),
                          min_value=df.index.min(),
                          max_value=df.index.max(),
                          key=1
                          )
    check=b.checkbox('Use Second Regime')
    b.markdown('**Second Regime**')
    regimeStartDate=b.date_input('Start Date',
                                  value=df.index.min(),
                                  min_value=df.index.min(),
                                  max_value=df.index.max()
                                  )
    regimeEndDate=b.date_input('End Date',
                                value=df.index.max(),
                                min_value=df.index.min(),
                                max_value=df.index.max()
                                )
    if check:
        df1=df.reindex(pd.date_range(start=regimeStartDate,
                                     end=regimeEndDate
                                     )
                       )
    
    df=df.reindex(pd.bdate_range(start=startDate,end=endDate))
    
    submitted=st.form_submit_button('Submit')    
    
    if submitted:
        y=df[seriesD][np.logical_not(np.isnan(df[seriesD]))]
        X=df[seriesI][np.logical_not(np.isnan(df[seriesI]))]
        x=X.values.reshape(-1,1)
        linear_regressor=LinearRegression()
        linear_regressor.fit(x,y)
        x_range=np.linspace(x.min(),x.max(),100)
        y_range=linear_regressor.predict(x_range.reshape(-1,1))
        columns=['Regime 1']
        data=["{:0.2f}".format(linear_regressor.coef_[0]),
                        "{:0.2f}".format(linear_regressor.intercept_),
                        "{:0.2f}".format(scipy.stats.pearsonr(X,y)[0]),
                        str(len(x))
            ]
        if check:
            y1=df1[seriesD][np.logical_not(np.isnan(df1[seriesD]))]
            X1=df1[seriesI][np.logical_not(np.isnan(df1[seriesI]))]
            x1=X1.values.reshape(-1,1)
            linear_regressor1=LinearRegression()
            linear_regressor1.fit(x1,y1)
            x1_range=np.linspace(x1.min(),x1.max(),100)
            y1_range=linear_regressor1.predict(x1_range.reshape(-1,1))
            columns.append('Regime 2')
            r2Data=["{:0.2f}".format(linear_regressor1.coef_[0]),
                        "{:0.2f}".format(linear_regressor1.intercept_),
                        "{:0.2f}".format(scipy.stats.pearsonr(X1,y1)[0]),
                        str(len(x1))
                    ]
            data=list(zip(data,r2Data))
        st.markdown('**Regression Statistics**')
        index=['Coefficient','Intercept','Correlation','Observations']

        regressionStats=pd.DataFrame(data,index=index,columns=columns)        
        st.dataframe(regressionStats)
        #fig1=px.scatter(df,x=seriesI,y=seriesD,
        #                )
        fig1=go.Figure()    
        fig1.add_trace(go.Scatter(x=df[seriesI],y=df[seriesD],
                                  mode='markers',
                                  name='Regime 1')
                       )
        fig1.add_trace(go.Scatter(x=x_range,y=y_range,name='Regime 1 Fit'))
        if check:
            fig1.add_trace(go.Scatter(x=x1_range,y=y1_range,
                                      name='Regime 2 Fit',
                                      fillcolor='purple')
                           )
            fig1.add_trace(go.Scatter(x=df1[seriesI],y=df1[seriesD],
                                      mode='markers',
                                      name='Regime 2')
                           )
        fig1.update_layout(xaxis_title=seriesI,
                           yaxis_title=seriesD)
        st.plotly_chart(fig1)    
    
with st.form('rolling'):    
    st.subheader('Rolling Correlation Analysis')
    col2, col3, col4=st.columns(3)
    d1=col2.number_input('Enter Number of Days',min_value=2,step=1,value=5)
    d2=col3.number_input('Enter Number of Days',min_value=2,step=1,value=10)
    d3=col4.number_input('Enter Number of Days',min_value=2,step=1,value=20)
    
    submittedRolling=st.form_submit_button('Submit')
    
    if submittedRolling:
        df.dropna(inplace=True)
        index=['Last','Mean','Median','StDev','Min','Max']
        
        ##Rolling Correlations
        columns=[str(d1)+'d',str(d2)+'d',str(d3)+'d']
        data={}
        charts=[]
        for period in [d1,d2,d3]:
            s=df[seriesI].rolling(period).corr(df[seriesD])
        
            data[str(period)+'d']=["{:0.2f}".format(s[-1]),"{:0.2f}".format(s.mean()),
                   "{:0.2f}".format(s.median()),"{:0.2f}".format(s.std()),
                   "{:0.2f}".format(s.min()),"{:0.2f}".format(s.max())
                   ]
            charts.append((s,period))
            
        rollingCorrelations=pd.DataFrame(data,index=index,columns=columns)
                
        ##Rolling Standard Deviations
        columns=[[seriesI,seriesI,seriesI,seriesD,seriesD,seriesD],
                 [str(d1)+'d',str(d2)+'d',str(d3)+'d',
                 str(d1)+'d',str(d2)+'d',str(d3)+'d'
                 ]
                 ]
        data={}
        for period,series in [(d1,seriesI),(d2,seriesI),(d3,seriesI),
                              (d1,seriesD),(d2,seriesD),(d3,seriesD)
                              ]:
            s=df[series].rolling(period).std()
        
            data[(series,str(period)+'d')]=["{:0.2f}".format(s[-1]),"{:0.2f}".format(s.mean()),
                  "{:0.2f}".format(s.median()),"{:0.2f}".format(s.std()),
                  "{:0.2f}".format(s.min()),"{:0.2f}".format(s.max())
                  ]
        
        rollingStd=pd.DataFrame(data,index=index,
                                columns=pd.MultiIndex.from_arrays(columns))
        
        st.markdown('**Rolling Correlation Statistics**')
        st.dataframe(rollingCorrelations)
        
        st.markdown('**Rolling Standard Deviation Statistics**')
        st.dataframe(rollingStd)
        
        for chart,period in charts:
            fig=px.histogram(chart,title=str(period)+'d Correlations')
            st.plotly_chart(fig)
                
with st.form('hedgeRatio'):    
    st.subheader('Rolling Hedge Ratio Analysis')
    col2, col3, col4=st.columns(3)
    d1=col2.number_input('Enter Number of Days',min_value=2,step=1,value=5)
    d2=col3.number_input('Enter Number of Days',min_value=2,step=1,value=10)
    d3=col4.number_input('Enter Number of Days',min_value=2,step=1,value=20)
    
    submittedRollingHR=st.form_submit_button('Submit')
    
    if submittedRollingHR:
        dfHR.dropna(inplace=True)
        index=['Last','Mean','Median','StDev','Min','Max']
        columns=[str(d1)+'d',str(d2)+'d',str(d3)+'d']
        data={}
        series=[]
        for period in [d1,d2,d3]:
            p=dfHR[seriesI].diff().rolling(period).corr(dfHR[seriesD].diff())
            sI=dfHR[seriesI].diff().rolling(period).std()
            sD=dfHR[seriesD].diff().rolling(period).std()
            sHR=p*(sD/sI)
        
            data[str(period)+'d']=("{:0.2f}".format(sHR[-1]),"{:0.2f}".format(sHR.mean()),
                  "{:0.2f}".format(sHR.median()),"{:0.2f}".format(sHR.std()),
                  "{:0.2f}".format(sHR.min()),"{:0.2f}".format(sHR.max())
                  )
            series.append([sHR,period])
        
        rollingHR=pd.DataFrame(data,index=index,columns=columns)
                                    
        st.markdown('**Rolling Hedge Ratio Statistics**')
        st.dataframe(rollingHR)
        
        for series in series:
            fig=px.histogram(series[0],title=str(series[1])+'d Hedge Ratio')
            st.plotly_chart(fig)