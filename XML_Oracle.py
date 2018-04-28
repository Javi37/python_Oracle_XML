# -*- coding: utf-8 -*-
"""
Spyder Editor

Creation time: 3/19/18
Programmer: Javi Sanz

The goal is to read as series of tables from an Oracle RDBMS and generate 
an output in XML format.
The program iterates through a series of nested loops to  find the inner connections
between the different records

Each record is driven by each hospitalization record and the differente care events
associated with it:
    demographics
    encounter info
    PICU
    diagnoses
    procedures
    labs
    micro (?)

There is a series of XSD documents to ensure compliance
    
"""
#import os

import xml.etree.cElementTree as ET
import cx_Oracle
import time

def print_header(message):
    print('--------------------------------------------------------')
    print(message)
    print('--------------------------------------------------------')
    return

#------------------------------------------------------------------
#   Configure XML library and files   
#------------------------------------------------------------------
#root = ET.Element("AdmissionRecords")
root = ET.Element("CCDPDataSet")
root.set("xmlns","picu2")
root.set("xmlns:xsi","http://www.w3.org/2001/XMLSchema-instance")
Version = ET.SubElement(root, "Version").text = '1.1'
SiteInfo = ET.SubElement(root, "SiteInfo")
ET.SubElement(SiteInfo, "SiteAcronym").text = str('UCLA')

ts = time.gmtime()
print(time.strftime("%Y-%m-%d %H:%M:%S", ts))
start_time = str((time.strftime("%Y-%m-%d %H:%M:%S", ts)))
#------------------------------------------------------------------
#   Set up DB connection (need to hide credentials)
#------------------------------------------------------------------
print_header('connecto to DB')
conn_str = u'USERNAME/PASSWORD@HOST:PORT/SERVICE_NAME'
conn = cx_Oracle.connect(conn_str)

#------------------------------------------------------------------
#   Set up cursor to pull encounters
#------------------------------------------------------------------
encc = conn.cursor()
sql_enc = """
             SELECT DISTINCT coh.study_id
             ,enc.encounter_num
             ,to_char(enc.hosp_admsn_time,\'yyyy-mm-dd\') as hosp_admsn_date
             ,to_char(enc.hosp_admsn_time,\'HH24:mm:ss\') as hosp_admsn_time
             ,to_char(enc.hosp_dischrg_time,\'yyyy-mm-dd\') as hosp_dischrg_date
             ,to_char(enc.hosp_dischrg_time,\'HH24:mm:ss\') as hosp_dischrg_time
             ,CASE WHEN adm.visit_type IS NULL THEN \'-2\' ELSE adm.code END AdmissionTypeC
             ,enc.visit_type as AdmissionTypeN
             ,CASE WHEN ins.financial_class IS NULL THEN \'-2\' ELSE ins.code END PrimaryPayerC
             ,enc.financial_class as PrimaryPayerN
             ,CASE WHEN dis.DISCH_DISP_C IS NULL THEN '-2' ELSE dis.code END HospitalDischargeDispositionC
             ,enc.disposition as HospitalDischargeDispositionN
             FROM xdr_sapru_hong_enc         enc  
             JOIN xdr_sapru_hong_coh  		coh on enc.pat_id = coh.pat_id 
             JOIN xdr_sapru_hong_laball_f    lab on enc.encounter_num = lab.encounter_num
             left join xdr_sapru_hong_admission adm on enc.visit_type = adm.visit_type
             left join xdr_sapru_hong_insurance ins on enc.financial_class = ins.financial_class 
             left join xdr_sapru_hong_disposition dis on enc.DISCH_DISP_C = dis.DISCH_DISP_C 
             ORDER BY coh.study_id,enc.encounter_num """ 

encc.execute(sql_enc)        

enc_pat_params = {}
print_header('pull from encounters')
count = 1
encounter = 0
enc_dic = encc
AdmissionRecords = ET.SubElement(root, "AdmissionRecords")
for row in encc:
    # insert encounter and patient identifiers
    AdmissionRecord = ET.SubElement(AdmissionRecords, "AdmissionRecord")
    Identifications = ET.SubElement(AdmissionRecord, "Identifications")
    ET.SubElement(Identifications, "MRN", isEncrypted="false").text = row[0]
    ET.SubElement(Identifications, "VisitID", isEncrypted="false").text = str(row[1])
    study_id = row[0]
    encounter_num = row[1]
    enc_pat_params[row[0]] = [row[1]]

#------------------------------------------------------------------
#   Set up cursor to pull demographics
#------------------------------------------------------------------
    sql_dem = """
            SELECT  study_id    
                    ,to_char(birth_date,\'yyyy-mm-dd\') as "BirthDate"
                    ,CASE WHEN sx.code IS NULL THEN \'-2\' ELSE sx.code END SexC
                    ,pat.sex as SexN
                    ,CASE WHEN rc.code IS NULL THEN \'-2\' ELSE rc.code END RaceC
                    ,pat.race as RaceN
                    ,CASE WHEN et.code IS NULL THEN \'-2\' ELSE et.code END EthnicityC
                    ,et.ETHNICITY as EthnicityN
                    from xdr_sapru_hong_pat pat
                    left join xdr_sapru_hong_sex sx on pat.SEX_C = sx.SEX_C
                    left join xdr_sapru_hong_race rc on pat.MAPPED_RACE_C = rc.MAPPED_RACE_C
                    left join xdr_sapru_hong_ethnicity et on pat.ETHNIC_GROUP_C = et.ETHNIC_GROUP_C
                    where study_id =:study_id  """    
    demo = conn.cursor()
    demo.execute(sql_dem,{'study_id':study_id})
    for pat in demo:
        Demographics = ET.SubElement(AdmissionRecord, "Demographics")
        ET.SubElement(Demographics, "BirthDate").text = str(pat[1])
        ET.SubElement(Demographics, "Sex",  SexID= str(pat[2])).text = str(pat[3])
        ET.SubElement(Demographics, "Race", RaceID=str(pat[4])).text = str(pat[4])
        ET.SubElement(Demographics, "Ethnicity", EthnicityID=str(pat[6])).text = str(pat[6])
        HospitalAdmissionInfo = ET.SubElement(AdmissionRecord, "HospitalAdmissionInfo")
        HospitalAdmitDateTime = ET.SubElement(HospitalAdmissionInfo, "HospitalAdmitDateTime")
        ET.SubElement(HospitalAdmitDateTime, "Date").text = str(row[2])
        ET.SubElement(HospitalAdmitDateTime, "Time").text = str(row[3])
        HospitalDischargeDateTime = ET.SubElement(HospitalAdmissionInfo, "HospitalDischargeDateTime")
        ET.SubElement(HospitalDischargeDateTime, "Date").text = str(row[4])
        ET.SubElement(HospitalDischargeDateTime, "Time").text = str(row[5])
        # opending mapping from PI
        ET.SubElement(HospitalAdmissionInfo, "AdmissionType", AdmissionTypeID = str(row[6])).text = str(row[7])
        ET.SubElement(HospitalAdmissionInfo, "PrimaryPayer", PrimaryPayerTypeID = str(row[8])).text = str(row[9])
        ET.SubElement(HospitalAdmissionInfo, "HospitalDischargeDisposition", DischargeDispositionTypeID = str(row[10])).text = str(row[11])   
    t = demo.fetchall()

#------------------------------------------------------------------
#   Set up cursor to pull diagnosis
#------------------------------------------------------------------
    sql_dx = """
            SELECT DISTINCT ICD_CODE
            FROM XDR_SAPRU_HONG_ENCDX
            WHERE ENCOUNTER_NUM =:encounter_num
            """
    #print(sql)
    dx = conn.cursor()
    dx.execute(sql_dx,{'encounter_num':encounter_num})
    DiagnosisCodeGroup = ET.SubElement(AdmissionRecord, "DiagnosisCodeGroup")
    for dxcode in dx:
        ET.SubElement(DiagnosisCodeGroup, "DxCodeICD10").text = str(dxcode[0])
    d = dx.fetchall()
#------------------------------------------------------------------
#   Set up cursor to pull procedures
#------------------------------------------------------------------    
    sql_prc = """
            SELECT DISTINCT PROC_CODE
            FROM XDR_SAPRU_HONG_PRC
            WHERE ENCOUNTER_NUM =:encounter_num
            """
    px = conn.cursor()
    px.execute(sql_prc,{'encounter_num':encounter_num})
    ProcedureCodeGroup = ET.SubElement(AdmissionRecord, "ProcedureCodeGroup")
    for pxcode in px:
        ET.SubElement(ProcedureCodeGroup, "ProcCodeICD10").text = str(pxcode[0])
#------------------------------------------------------------------
#   Set up cursor to pull ADT - PICU
#------------------------------------------------------------------    
    sql_adt = """
            SELECT ENCOUNTER_NUM
                    ,to_char(TIME_IN,'yyyy-mm-dd')   TIME_IN_date
                    ,to_char(TIME_IN,'HH24:mm:ss')   TIME_IN_time
                    ,to_char(TIME_OUT,'yyyy-mm-dd')   TIME_OUT_date
                    ,to_char(TIME_OUT,'HH24:mm:ss')   TIME_OUT_time
            FROM XDR_SAPRU_HONG_ADT
            WHERE ENCOUNTER_NUM =:encounter_num
            """
    adt = conn.cursor()
    adt.execute(sql_adt,{'encounter_num':encounter_num})
    PicuDateTimeGroup = ET.SubElement(AdmissionRecord, "PicuDateTimeGroup")
    for adtrec in adt:
        PicuInfo = ET.SubElement(PicuDateTimeGroup, "PicuInfo")
        PicuDateTime = ET.SubElement(PicuInfo, "PicuDateTime")
        PicuAdminDateTime = ET.SubElement(PicuDateTime, "PicuAdminDateTime")
        ET.SubElement(PicuAdminDateTime, "Date").text = str(adtrec[1])
        ET.SubElement(PicuAdminDateTime, "Time").text = str(adtrec[2])
        PicuDischargeDateTime = ET.SubElement(PicuDateTime, "PicuDischargeDateTime")
        ET.SubElement(PicuDischargeDateTime, "Date").text = str(adtrec[3])
        ET.SubElement(PicuDischargeDateTime, "Time").text = str(adtrec[4])
    a = adt.fetchall()
#------------------------------------------------------------------
#   Set up cursor to pull Labs ()
#------------------------------------------------------------------     
    sql_lab = """
            SELECT DISTINCT lab.ORDER_PROC_ID
                ,lab.PROC_CODE
                ,lab.DESCRIPTION
                ,to_char(lab.ORDER_TIME,'yyyy-mm-dd')   order_date
                ,to_char(lab.ORDER_TIME,'HH24:mm:ss')   order_time
                ,to_char(lab.SPECIMN_TAKEN_TIME,'yyyy-mm-dd')   specimn_date
                ,to_char(lab.SPECIMN_TAKEN_TIME,'HH24:mm:ss')   specimn_time
                ,lab.SOURCE_NAME
                ,lab.SPECIMEN_SOURCE_C
                ,lab.ENCOUNTER_NUM
                ,lab.speciment_type_name
            FROM xdr_sapru_hong_laball_f lab   
            WHERE ENCOUNTER_NUM =:encounter_num
            ORDER BY ORDER_PROC_ID
            """
    lb = conn.cursor()
    lb.execute(sql_lab,{'encounter_num':encounter_num})
#------------------------------------------------------------------
#   Set up cursor to pull Labs results (components into each panel definwd by order_proc_id)
#------------------------------------------------------------------    
    lab_count = 1
    component_count = 1
    dummy = 0
    LabGroup = ET.SubElement(AdmissionRecord, "LabGroup")
    for lab in lb:
        test_code = str(lab[0])
        Lab = ET.SubElement(LabGroup, "Lab")
        ET.SubElement(Lab, "BatteryCode").text = str(lab[0])
        ET.SubElement(Lab, "TestCode").text = str(lab[1])
        ET.SubElement(Lab, "TestName").text = str(lab[2])       
        LabOrderDateTime = ET.SubElement(Lab, "LabOrderDateTime")
        ET.SubElement(LabOrderDateTime, "Date").text = str(lab[3])
        ET.SubElement(LabOrderDateTime, "Time").text = str(lab[4])
        Specimen = ET.SubElement(Lab, "Specimen")
        if str(lab[5]) == 'None':
            dummy = dummy +1 
            #print('date not found:' + str(lab[5]) + '"')
        else:
            CollectionDateTime = ET.SubElement(Specimen, "CollectionDateTime")
            ET.SubElement(CollectionDateTime, "Date").text = str(lab[5])
            ET.SubElement(CollectionDateTime, "Time").text = str(lab[6])
            #print('date found' + str(lab[5]) + '"')
        ET.SubElement(Specimen, "SpecimenName").text = str(lab[10])
        SpecimenSource = ET.SubElement(Specimen, "SpecimenSource")
        ET.SubElement(SpecimenSource, "BodySiteCode").text = str(lab[8])
        ET.SubElement(SpecimenSource, "BodySiteName").text = str(lab[7])

        sql_lb_dtl = """
            SELECT DISTINCT component_id
                ,component_name
                ,ord_value
                ,reference_unit
                ,to_char(RESULT_TIME,'yyyy-mm-dd')   result_date
                ,to_char(RESULT_TIME,'HH24:mm:ss')   result_time
                ,REF_NORMAL_VALS reference
                ,ORDER_PROC_ID
                ,CASE WHEN BIP_LOINC_MAPPING IS NULL THEN \'-0\' ELSE BIP_LOINC_MAPPING END
            FROM xdr_sapru_hong_laball_f
            WHERE ORDER_PROC_ID =: test_code
            """
        lb_dtl = conn.cursor()
        lb_dtl.execute(sql_lb_dtl,{'test_code':test_code,})
        lab_count = lab_count + 1
        #print(lab)
        Results = ET.SubElement(Lab, "Results")        
#        print(                  
#                  #' order_proc_id: ' + str(component[7]) + 
#                  ' panel: ' + str(lab[2]) +
#                  #' component: ' + str(component[1]) + 
#                  ' and order proc count: ' + str(lab_count) + 
#                  ' and component count: ' + str(component_count)
#                  )
        for component in lb_dtl:
            #print(str(component[1]))
            component_count = component_count + 1
            Result = ET.SubElement(Results, "Result")
            ResultDateTime = ET.SubElement(Result, "ResultDateTime")
            Reference = ET.SubElement(Result, "Reference")
            ET.SubElement(ResultDateTime, "Date").text = str(component[4])
            ET.SubElement(ResultDateTime, "Time").text = str(component[5])
            ET.SubElement(Result, "ResultName").text = str(component[1])
            ET.SubElement(Result, "LOINC").text = str(component[8])
            ET.SubElement(Result, "ResultValue").text = str(component[2])
            ET.SubElement(Result, "ResultUnit").text = str(component[3])
            ET.SubElement(Reference, "Range").text = str(component[6])
#            print(                  
#                  ' order_proc_id: ' + str(component[7]) + 
#                  ' panel: ' + str(lab[2]) +
#                  ' component: ' + str(component[1]) + 
#                  ' and order proc count: ' + str(lab_count) + 
#                  ' and component count: ' + str(component_count)
#                  )
    print('Processed encounter number ' + str(count) + ' Related to encounter_num: ' + str(encounter_num)+ ' and order proc count: ' + str(lab_count) + ' and component count: ' + str(component_count))
    count = count + 1
print_header('Finish extracting data')
conn.close()
print_header('Start XML export')
tree = ET.ElementTree(root)
tree.write("Data_Sapru_Hong_17-000140_ALL_RECORDS.xml",encoding='UTF-8', xml_declaration=True)  
print(start_time)
print('final time')
ts = time.gmtime()
print(time.strftime("%Y-%m-%d %H:%M:%S", ts))