/**
 * ฟังก์ชันคำนวณ Error Metrics (MSE, RMSE, MAE)
 * โดยใช้ข้อมูลจาก predicted (array ของตัวเลข) และ actual (array ของตัวเลข)
 */
function calculateErrorMetrics(predicted, actual) {
  const n = Math.min(predicted.length, actual.length);
  if (n === 0) {
    return { mse: 0, rmse: 0, mae: 0 };
  }
  let sumSquaredError = 0;
  let sumAbsoluteError = 0;
  for (let i = 0; i < n; i++) {
    const error = predicted[i] - actual[i];
    sumSquaredError += error * error;
    sumAbsoluteError += Math.abs(error);
  }
  const mse = sumSquaredError / n;
  const rmse = Math.sqrt(mse);
  const mae = sumAbsoluteError / n;
  return { mse, rmse, mae };
}

/**
 * ฟังก์ชันดึงค่าพารามิเตอร์จากอินพุตในหน้า HTML
 */
function getParameters() {
  return {
    Psh: parseFloat(document.getElementById("Psh").value) || 0,
    R_TR: parseFloat(document.getElementById("R_TR").value) || 0,
    P_F: parseFloat(document.getElementById("P_F").value) || 0,
    OL: parseFloat(document.getElementById("OL").value) || 0,
    RF: parseFloat(document.getElementById("RF").value) || 0,
    N: parseFloat(document.getElementById("N").value) || 0,
    battery_size: parseFloat(document.getElementById("battery_size").value) || 0,
    Power_bat_max: parseFloat(document.getElementById("Power_bat_max").value) || 0,
    start_time: parseInt(document.getElementById("start_time").value) || 0,
    end_time: parseInt(document.getElementById("end_time").value) || 0
  };
}

/**
 * ฟังก์ชันหลักที่ใช้ดึงข้อมูลจาก API ทั้งหมดและอัปเดตกราฟและส่วนแสดงผล
 */
async function fetchAndDisplayData() {
  try {
    console.log("🔍 Fetching data from APIs...");
    const params = getParameters();
    const building = "h2";
    const selectedDate = document.getElementById("selectedDate").value || "2024-01-05";
    const model = document.getElementById("model").value || "LSTM";

    // ดึงข้อมูลการพยากรณ์จาก API /get_predictions_by_date
    const predictionsResponse = await fetchPredictionsByDate(building, selectedDate, model);
    console.log("✅ predictionsResponse:", predictionsResponse);
    // เนื่องจาก API ส่งกลับเป็น object ที่มี key "predictions" เป็น array
    // สมมุติว่าเราใช้เฉพาะ element แรกใน array และใน element นั้นมี key "predictions" เป็น array ของ forecast values
    const forecastData = predictionsResponse.length > 0 ? predictionsResponse[0].predictions : [];

    // ดึงข้อมูล Actual Load จาก API /get_realtime_data_by_date
    const realtimeData = await fetchRealtimeDataByDate(building, selectedDate);
    console.log("✅ realtimeData:", realtimeData);

    // ดึงข้อมูลพลังงานจาก API /calculate_power (ใช้พารามิเตอร์รวม)
    const powerParams = { ...params, building, model, date: selectedDate };
    const powerResponse = await fetchPowerData(powerParams);
    console.log("📊 powerResponse:", powerResponse);

    const extractedData = extractEnergyValues(powerResponse);
    updateEnergyDisplay("combinedChart", extractedData);

    // ดึงข้อมูล CBL จาก API /calculate_cbl_by_date
    const cblData = await fetchCBLData(selectedDate);
    console.log("✅ cblData:", cblData);

    // คำนวณ Error Metrics จากค่า forecast กับ actual
    // สมมุติว่า forecast values อยู่ใน field "value" ของ forecastData
    const predictedValues = forecastData.map(item => item.value);
    const actualValues = realtimeData.map(item => item.raw_p_h);
    const errorMetrics = calculateErrorMetrics(predictedValues, actualValues);
    console.log("✅ Error Metrics:", errorMetrics);

    // อัปเดตส่วนแสดงผลสำหรับ Error Metrics
    document.getElementById("mse_combinedChart").textContent = errorMetrics.mse.toFixed(2);
    document.getElementById("rmse_combinedChart").textContent = errorMetrics.rmse.toFixed(2);
    document.getElementById("mae_combinedChart").textContent = errorMetrics.mae.toFixed(2);

    // อัปเดตกราฟด้วย Chart.js หากข้อมูลครบถ้วน
    if (powerResponse.results && forecastData.length > 0 && cblData.length > 0 && realtimeData.length > 0) {
      updateChart(powerResponse.results, forecastData, cblData, realtimeData, "combinedChart", params.Psh);
    }
  } catch (error) {
    console.error("❌ Error fetching data:", error);
    alert("Error fetching data. Check console for details.");
  }
}

/**
 * ฟังก์ชันดึงข้อมูลการพยากรณ์จาก API `/get_predictions_by_date`
 */
async function fetchPredictionsByDate(building, date, model = "LSTM") {
  try {
    console.log("🔍 Fetching /get_predictions_by_date...");
    const response = await fetch(`http://127.0.0.1:5000/get_predictions_by_date?building=${building}&model=${model}&date=${date}`);
    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
    const data = await response.json();
    return data.predictions ?? [];
  } catch (error) {
    console.error("❌ Failed to fetch /get_predictions_by_date:", error);
    return [];
  }
}

/**
 * ฟังก์ชันดึงข้อมูลจาก API `/calculate_power`
 */
async function fetchPowerData(powerParams) {
  try {
    console.log("🔍 Fetching /calculate_power...");
    const response = await fetch("http://127.0.0.1:5000/calculate_power", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(powerParams)
    });
    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
    const data = await response.json();
    console.log("✅ Data received from API /calculate_power:", data);
    return data;
  } catch (error) {
    console.error("❌ Failed to fetch /calculate_power:", error);
    return {};
  }
}

/**
 * ฟังก์ชันดึงข้อมูลจาก API `/calculate_cbl_by_date`
 */
async function fetchCBLData(date) {
  try {
    console.log("🔍 Fetching /calculate_cbl_by_date...");
    const response = await fetch(`http://127.0.0.1:5000/calculate_cbl_by_date?building=h2&date=${date}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" }
    });
    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
    const data = await response.json();
    return data.cbl ?? [];
  } catch (error) {
    console.error("❌ Failed to fetch /calculate_cbl_by_date:", error);
    return [];
  }
}

/**
 * ฟังก์ชันดึงข้อมูล realtime จาก API `/get_realtime_data_by_date`
 */
async function fetchRealtimeDataByDate(building, date) {
  try {
    console.log("🔍 Fetching /get_realtime_data_by_date...");
    const response = await fetch(`http://127.0.0.1:5000/get_realtime_data_by_date?building=${building}&date=${date}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" }
    });
    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
    const data = await response.json();
    return data.realtime_data ?? [];
  } catch (error) {
    console.error("❌ Failed to fetch /get_realtime_data_by_date:", error);
    return [];
  }
}

/**
 * ฟังก์ชันดึงค่า Energy Metrics จาก response ของ API calculate_power
 * รวมถึงค่า MSE, RMSE, MAE ที่ได้จาก API (ในกรณีที่ API ส่งกลับค่าเหล่านี้)
 */
function extractEnergyValues(data) {
  return {
    P_Peak_New: data.P_Peak_New ?? 0,
    Reduction_Peak: data.Reduction_Peak ?? 0,
    time_period: data.time_period?.length ? data.time_period : ["-"],
    starttimes: data.starttimes?.length ? data.starttimes : ["-"],
    endtimes: data.endtimes?.length ? data.endtimes : ["-"],
    Total_Electricity_Cost: data.Total_Electricity_Cost ?? 0,
    Total_Carbon_Emission: data.Total_Carbon_Emission ?? 0,
    mse: data.mse ?? 0,
    rmse: data.rmse ?? 0,
    mae: data.mae ?? 0
  };
}

/**
 * ฟังก์ชันอัปเดตแสดงค่า Energy Metrics บนหน้าเว็บ
 */
function updateEnergyDisplay(chartId, data) {
  document.getElementById(`P_Peak_New_${chartId}`).textContent = (data.P_Peak_New ?? 0).toFixed(2) + " kW/Day";
  document.getElementById(`Reduction_Peak_${chartId}`).textContent = (data.Reduction_Peak ?? 0).toFixed(2) + " kW";
  document.getElementById(`time_period_${chartId}`).textContent = data.time_period.length ? data.time_period.join(", ") : "-";
  document.getElementById(`starttimes_${chartId}`).textContent = data.starttimes.length ? data.starttimes.join(", ") : "-";
  document.getElementById(`endtimes_${chartId}`).textContent = data.endtimes.length ? data.endtimes.join(", ") : "-";
  document.getElementById(`Total_Electricity_Cost_${chartId}`).textContent = (data.Total_Electricity_Cost ?? 0).toFixed(2) + " ฿";
  document.getElementById(`Total_Carbon_Emission_${chartId}`).textContent = (data.Total_Carbon_Emission ?? 0).toFixed(2) + " kg CO2";
  // แสดงผล Error Metrics
  document.getElementById(`mse_${chartId}`).textContent = data.mse.toFixed(2);
  document.getElementById(`rmse_${chartId}`).textContent = data.rmse.toFixed(2);
  document.getElementById(`mae_${chartId}`).textContent = data.mae.toFixed(2);
}

/**
 * ฟังก์ชันสร้างข้อมูลกราฟจากข้อมูล API ที่ได้รับ
 * รวมทั้งชุดข้อมูล Actual Load ที่ได้จาก API realtime
 * และคำนวณความคลาดเคลื่อน (Error) ระหว่าง forecast กับ actual (แต่ไม่แสดงในกราฟ)
 */
function generateChartData(powerResults, predictionData, cblData, realtimeData, chartId, Psh) {
  const timestamps = powerResults.map(item => item.timestamp);
  const P_ForecastingValues = powerResults.map(item => item.P_forecasting);
  const P_NewValues = powerResults.map(item => item.P_New);
  const P_BatValues = powerResults.map(item => item.P_Bat);
  // สำหรับ Actual Load, ใช้ field raw_p_h จาก realtimeData
  const actualValues = realtimeData.map(item => item.raw_p_h);
  const P_Bat_AdjustedValues = P_BatValues.map(value => value * 0.81);
  const Adjusted_Load_Values = actualValues.map((value, index) => value - (P_Bat_AdjustedValues[index] || 0));

  // คำนวณค่า Adjusted_Load เป็นรายชั่วโมง (สมมติว่าข้อมูลแบ่งเป็น 15 นาที)
  let Adjusted_Load_Hourly = [];
  for (let i = 0; i < Adjusted_Load_Values.length; i += 4) {
    let sum_kWh = Adjusted_Load_Values.slice(i, i + 4).reduce((acc, val) => acc + val, 0) / 4;
    Adjusted_Load_Hourly.push(sum_kWh);
  }
  // คำนวณความแตกต่าง (Difference) ระหว่าง CBL กับ Adjusted Load
  let Difference_Load_Hourly = cblData.map((cbl, index) => (cbl?.CBL || 0) - Adjusted_Load_Hourly[index]);

  // ฟังก์ชันแสดงผลรวมในหน้าเว็บ
  function updateDifferenceLoadDisplay(Difference_Load_Hourly) {
    let listElement = document.getElementById("difference_load_hourly_list");
    listElement.innerHTML = "";
    let totalDifferenceLoad = Difference_Load_Hourly.reduce((sum, value) => sum + value, 0);
    const constantMultiplier = 4;
    const constantMultiplier1 = 0.5;
    document.getElementById("Total_Difference_Load").textContent = (totalDifferenceLoad * constantMultiplier).toFixed(2) + " ฿";
    document.getElementById("Total_Difference_Load2").textContent = (totalDifferenceLoad * constantMultiplier1).toFixed(2) + " kg CO2";
    console.log("📊 Total Difference Load:", totalDifferenceLoad);
    return totalDifferenceLoad;
  }
  const totalLoad = updateDifferenceLoadDisplay(Difference_Load_Hourly);

  let adjustedCblValues = new Array(96).fill(null);
  cblData.forEach((c, index) => {
    let hourlyIndex = index * 4;
    adjustedCblValues[hourlyIndex] = c.CBL;
  });
  const PshValues = new Array(timestamps.length).fill(Psh);

  return {
    labels: timestamps,
    datasets: [
      {
        label: "Load Forecasting",
        data: P_ForecastingValues,
        borderColor: "#1f78b4",
        backgroundColor: "rgba(31, 120, 180, 0.2)",
        fill: true
      },
      {
        label: "New Load Based on Ems",
        data: P_NewValues,
        borderColor: "#33a02c",
        backgroundColor: "rgba(51, 160, 44, 0.2)",
        fill: true
      },
      {
        label: "Battery Power Scheduling",
        data: P_BatValues,
        borderColor: "#6a3d9a",
        backgroundColor: "rgba(106, 61, 154, 0.2)",
        fill: true
      },
      {
        label: "Baseline Load (CBL)",
        data: adjustedCblValues,
        borderColor: "#ff7f00",
        borderDash: [5, 5],
        borderWidth: 2,
        spanGaps: true,
        fill: false
      },
      {
        label: "Overload Limit",
        data: PshValues,
        borderColor: "#e31a1c",
        borderDash: [10, 5],
        borderWidth: 2,
        fill: false
      },
      {
        label: "Actual Load",
        data: actualValues,
        borderColor: "#000000",
        backgroundColor: "rgba(0, 0, 0, 0.2)",
        fill: false
      }
    ]
  };
}

/**
 * ฟังก์ชันอัปเดตกราฟในหน้า HTML โดยใช้ Chart.js
 */
function updateChart(powerResults, predictionData, cblData, realtimeData, chartId, Psh) {
  console.log(`📊 Updating chart: ${chartId}`);
  const ctx = document.getElementById(chartId).getContext("2d");
  if (window[chartId] instanceof Chart) {
    window[chartId].destroy();
  }
  window[chartId] = new Chart(ctx, {
    type: "line",
    data: generateChartData(powerResults, predictionData, cblData, realtimeData, chartId, Psh),
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: "Time (Hourly Intervals)" } },
        y: { title: { display: true, text: "Load Power (kW)" } }
      }
    }
  });
}

/**
 * ฟังก์ชันเรียกใช้งานเมื่อผู้ใช้คลิกปุ่ม "Load Data"
 */
function onLoadData() {
  fetchAndDisplayData();
}
