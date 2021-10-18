# Databricks notebook source
# MAGIC 
# MAGIC %md-sandbox
# MAGIC 
# MAGIC <div style="text-align: center; line-height: 0; padding-top: 9px;">
# MAGIC   <img src="https://databricks.com/wp-content/uploads/2018/03/db-academy-rgb-1200px.png" alt="Databricks Learning" style="width: 600px">
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # XGBoost
# MAGIC 
# MAGIC Up until this point, we have only used SparkML. Let's look a third party library for Gradient Boosted Trees. 
# MAGIC  
# MAGIC Ensure that you are using the [Databricks Runtime for ML](https://docs.microsoft.com/en-us/azure/databricks/runtime/mlruntime) because that has Distributed XGBoost already installed. 
# MAGIC 
# MAGIC **Question**: How do gradient boosted trees differ from random forests? Which parts can be parallelized?
# MAGIC 
# MAGIC ## ![Spark Logo Tiny](https://files.training.databricks.com/images/105/logo_spark_tiny.png) In this lesson you:<br>
# MAGIC  - Use 3rd party libraries (XGBoost) to further improve your model

# COMMAND ----------

# MAGIC %run "./Includes/Classroom-Setup"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Preparation
# MAGIC 
# MAGIC Let's go ahead and index all of our categorical features, and set our label to be `log(price)`.

# COMMAND ----------

from pyspark.sql.functions import log, col
from pyspark.ml.feature import StringIndexer, VectorAssembler
from pyspark.ml import Pipeline

filePath = f"{datasets_dir}/airbnb/sf-listings/sf-listings-2019-03-06-clean.delta/"
airbnbDF = spark.read.format("delta").load(filePath)
trainDF, testDF = airbnbDF.withColumn("label", log(col("price"))).randomSplit([.8, .2], seed=42)

categoricalCols = [field for (field, dataType) in trainDF.dtypes if dataType == "string"]
indexOutputCols = [x + "Index" for x in categoricalCols]

stringIndexer = StringIndexer(inputCols=categoricalCols, outputCols=indexOutputCols, handleInvalid="skip")

numericCols = [field for (field, dataType) in trainDF.dtypes if ((dataType == "double") & (field != "price") & (field != "label"))]
assemblerInputs = indexOutputCols + numericCols
vecAssembler = VectorAssembler(inputCols=assemblerInputs, outputCol="features")
pipeline = Pipeline(stages=[stringIndexer, vecAssembler])

# COMMAND ----------

# MAGIC %md
# MAGIC ### Pyspark Distributed XGBoost
# MAGIC 
# MAGIC Let's create our distributed XGBoost model. While technically not part of MLlib, you can integrate [XGBoost](https://databricks.github.io/spark-deep-learning/_modules/sparkdl/xgboost/xgboost.html) into your ML Pipelines. 
# MAGIC 
# MAGIC To use the distributed version of Pyspark XGBoost you can specify two additional parameters:
# MAGIC 
# MAGIC * `num_workers`: The number of workers to distribute over. Requires MLR 9.0+.
# MAGIC * `use_gpu`: Enable to utilize GPU based training for faster performance (optional).
# MAGIC 
# MAGIC **NOTE:** `use_gpu` requires an ML GPU runtime. Currently, at most one GPU per worker will be used when doing distributed training. 

# COMMAND ----------

from sparkdl.xgboost import XgboostRegressor

params = {"n_estimators": 100, "learning_rate": 0.1, "max_depth": 4, "random_state": 42, "missing": 0}

xgboost = XgboostRegressor(**params)

pipeline = Pipeline(stages=[stringIndexer, vecAssembler, xgboost])
pipelineModel = pipeline.fit(trainDF)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evaluate
# MAGIC 
# MAGIC Now we can evaluate how well our XGBoost model performed. Don't forget to exponentiate!

# COMMAND ----------

from pyspark.sql.functions import exp, col

logPredDF = pipelineModel.transform(testDF)

expXgboostDF = logPredDF.withColumn("prediction", exp(col("prediction")))

display(expXgboostDF.select("price", "prediction"))

# COMMAND ----------

# MAGIC %md
# MAGIC Compute some metrics.

# COMMAND ----------

from pyspark.ml.evaluation import RegressionEvaluator

regressionEvaluator = RegressionEvaluator(predictionCol="prediction", labelCol="price", metricName="rmse")

rmse = regressionEvaluator.evaluate(expXgboostDF)
r2 = regressionEvaluator.setMetricName("r2").evaluate(expXgboostDF)
print(f"RMSE is {rmse}")
print(f"R2 is {r2}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Alternative Gradient Boosted Approaches
# MAGIC 
# MAGIC There are lots of other gradient boosted approaches, such as [CatBoost](https://catboost.ai/), [LightGBM](https://github.com/microsoft/LightGBM), vanilla gradient boosted trees in [SparkML](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.ml.classification.GBTClassifier.html?highlight=gbt#pyspark.ml.classification.GBTClassifier)/[scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingClassifier.html), etc. Each of these has their respective [pros and cons](https://towardsdatascience.com/catboost-vs-light-gbm-vs-xgboost-5f93620723db) that you can read more about. 

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC &copy; 2021 Databricks, Inc. All rights reserved.<br/>
# MAGIC Apache, Apache Spark, Spark and the Spark logo are trademarks of the <a href="http://www.apache.org/">Apache Software Foundation</a>.<br/>
# MAGIC <br/>
# MAGIC <a href="https://databricks.com/privacy-policy">Privacy Policy</a> | <a href="https://databricks.com/terms-of-use">Terms of Use</a> | <a href="http://help.databricks.com/">Support</a>
