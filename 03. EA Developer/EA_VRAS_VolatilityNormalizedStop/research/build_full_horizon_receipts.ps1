
param([ValidateSet('pair','control','challenger')][string]$TargetArm='pair')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$package=Join-Path $repo '03. EA Developer\EA_VRAS_VolatilityNormalizedStop'
$preflight=Join-Path $package 'research\preflight\HYP-VRAS-EURUSD-M5-007'
$source=Join-Path $package 'EA_VRAS_VolatilityNormalizedStop.mq5'
$binary=Join-Path $package 'EA_VRAS_VolatilityNormalizedStop.ex5'
$prereg=Join-Path $package 'research\HYP-VRAS-EURUSD-M5-007_FULL_HORIZON_DIAGNOSTIC_PLAN.md'
$probe=Join-Path $package 'research\HYP-VRAS-EURUSD-M5-007_FULL_HORIZON_DIAGNOSTIC_PLAN.md'
$contract=Join-Path $package 'ALPHAFACTORY_EA_CONTRACT.json'
$auditManifest=Join-Path $package 'NONREPAINT_AUDIT_HYP007_manifest.json'
$audit=Join-Path $package 'research\evidence\HYP-VRAS-EURUSD-M5-007_NONREPAINT_AUDIT.json'
$registry=Join-Path $repo '04. Memory\research\CANDIDATE_REGISTRY.jsonl'
$cost=Join-Path $preflight 'cost_source_manifest.unverified.json'
function FileSha([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToUpperInvariant()}
function TextSha([string]$s){$h=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($h.ComputeHash([Text.UTF8Encoding]::new($false).GetBytes($s)))).Replace('-','')}finally{$h.Dispose()}}
function WriteJson($v,[string]$p){[IO.File]::WriteAllText($p,($v|ConvertTo-Json -Depth 16)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))}
$arms=@([ordered]@{name='control';role='control';tag='CONTROL_FIXED_CLAMP_FULL_HORIZON';flag='false'},[ordered]@{name='challenger';role='challenger';tag='CHALLENGER_ATR_STRUCTURAL_FULL_HORIZON';flag='true'})
$chosen=if($TargetArm -eq 'pair'){$arms}else{@($arms|Where-Object{$_.name -eq $TargetArm})}
$registryLine=$null
foreach($line in Get-Content -LiteralPath $registry){$o=$line|ConvertFrom-Json;if([string]$o.hypothesis_id -ceq 'HYP-VRAS-EURUSD-M5-007'){$registryLine=[string]$line}}
if($null -eq $registryLine -or ($registryLine|ConvertFrom-Json).state -cne 'challenger'){throw 'Latest HYP007 registry row must be challenger'}
$common=@('InpDiagnosticDisableAccountDDEntryHalt=true','InpAtrFloorMultiple=1.0','InpAtrPeriod=14','InpBreakEvenOffsetPips=0.5','InpBreakEvenTriggerR=1.0','InpControlMaxSlPips=15.0','InpControlMinSlPips=4.0','InpDailyLossPct=1.50','InpEnableTelemetry=true','InpH1EmaPeriod=200','InpHypothesisId=HYP-VRAS-EURUSD-M5-007','InpMagic=5600757','InpMaxAccountDrawdownPct=6.00','InpMaxHoldBars=24','InpMaxSpreadPips=1.20','InpMaxStructuralAtrMultiple=3.0','InpMaxTradesPerDay=5','InpRequireNewsGuard=false','InpResearchAutoMode=true','InpRiskPercent=0.05','InpRiskRewardRatio=1.5','InpRollingVwapBars=48','InpSlBufferPips=1.5','InpSwingLookbackBars=10')
$gitCommit=(& git -C $repo rev-parse HEAD).Trim()
$gitStatus=@(& git -C $repo status --short --untracked-files=all|ForEach-Object{[string]$_})
$gitStatusSha=TextSha ([string]::Join([char]10,$gitStatus))
$results=@()
foreach($arm in $chosen){
  $taskPath=Join-Path $preflight "task_packet.$($arm.name).json"
  $receiptPath=Join-Path $preflight "contract_receipt.$($arm.name).json"
  $overrides=@($common+@("InpUseVolatilityNormalizedStop=$($arm.flag)","InpVariantTag=$($arm.tag)")|Sort-Object{($_ -split '=',2)[0]}) -join ';'
  $task=[ordered]@{schema_version='alphafactory_diagnostic_task_packet.v1';hypothesis_id='HYP-VRAS-EURUSD-M5-007';run_role=$arm.role;purpose='Frozen full-horizon no-account-DD-entry-halt Model-0 observation; diagnostic only';ea_name='EA_VRAS_VolatilityNormalizedStop';source_path='03. EA Developer/EA_VRAS_VolatilityNormalizedStop/EA_VRAS_VolatilityNormalizedStop.mq5';source_sha256=FileSha $source;registry_path='04. Memory/research/CANDIDATE_REGISTRY.jsonl';registry_sha256=FileSha $registry;registry_row_sha256=TextSha $registryLine;prereg_path='03. EA Developer/EA_VRAS_VolatilityNormalizedStop/research/HYP-VRAS-EURUSD-M5-007_FULL_HORIZON_DIAGNOSTIC_PLAN.md';prereg_sha256=FileSha $prereg;probe_plan_path='03. EA Developer/EA_VRAS_VolatilityNormalizedStop/research/HYP-VRAS-EURUSD-M5-007_FULL_HORIZON_DIAGNOSTIC_PLAN.md';probe_plan_sha256=FileSha $probe;symbol='EURUSD';period='M5';from='2019.01.01';to='2022.12.31';model=0;execution_mode=0;fixed_delay_ms=0;overrides=$overrides;telemetry_tier='trade-only';telemetry_profile='lifecycle-v3';required_sidecars=@('*_LifecycleTrades_*.csv','*_RunMeta_*.json','*_DecisionTelemetry_*.csv');deposit=100000;leverage=100;spread='current';cost_status='UNVERIFIED_DIAGNOSTIC_ONLY';news_guard='DISABLED_MATCHED';promotion_eligible=$false;git_commit=$gitCommit;git_status=$gitStatus;git_status_sha256=$gitStatusSha}
  WriteJson $task $taskPath
  $evidence=@([ordered]@{label='task_packet';kind='file';path=$taskPath;sha256=FileSha $taskPath},[ordered]@{label='candidate_registry';kind='file';path=$registry;sha256=FileSha $registry},[ordered]@{label='source';kind='file';path=$source;sha256=FileSha $source},[ordered]@{label='compiled_binary';kind='file';path=$binary;sha256=FileSha $binary},[ordered]@{label='ea_capability_contract';kind='file';path=$contract;sha256=FileSha $contract},[ordered]@{label='prereg';kind='file';path=$prereg;sha256=FileSha $prereg},[ordered]@{label='probe_plan';kind='file';path=$probe;sha256=FileSha $probe},[ordered]@{label='nonrepaint_manifest';kind='file';path=$auditManifest;sha256=FileSha $auditManifest},[ordered]@{label='nonrepaint_audit';kind='file';path=$audit;sha256=FileSha $audit},[ordered]@{label='cost_source_manifest';kind='file';path=$cost;sha256=FileSha $cost})
  if($arm.name -eq 'challenger'){
    $control=$null;$runRoot=Join-Path $repo '02. AlphaFactory\runs\EA_VRAS_VolatilityNormalizedStop'
    if(Test-Path $runRoot){foreach($dir in @(Get-ChildItem $runRoot -Directory|Sort-Object LastWriteTime -Descending)){$m=Join-Path $dir.FullName 'run_manifest.json';$r=Join-Path $dir.FullName 'report.html';if(!(Test-Path $m)-or!(Test-Path $r)){continue};$x=Get-Content $m -Raw|ConvertFrom-Json;if([string]$x.hypothesis_id -ceq 'HYP-VRAS-EURUSD-M5-007' -and [string]$x.run_role -ceq 'control'){$control=[ordered]@{manifest=$m;report=$r};break}}}
    if($null -eq $control){throw 'Completed HYP007 control required before challenger'}
    $evidence+=@([ordered]@{label='matched_control_manifest';kind='file';path=$control.manifest;sha256=FileSha $control.manifest},[ordered]@{label='matched_control_report';kind='file';path=$control.report;sha256=FileSha $control.report})
  }
  $binding=[ordered]@{hypothesis_id='HYP-VRAS-EURUSD-M5-007';run_role=$arm.role;ea_name='EA_VRAS_VolatilityNormalizedStop';symbol='EURUSD';period='M5';from='2019.01.01';to='2022.12.31';model=0;execution_mode=0;fixed_delay_ms=0;overrides=$overrides;telemetry_tier='trade-only';telemetry_profile='lifecycle-v3';deposit=100000;leverage=100;spread='current';required_sidecars=@('*_LifecycleTrades_*.csv','*_RunMeta_*.json','*_DecisionTelemetry_*.csv');broker_fingerprint='UNVERIFIED_DIAGNOSTIC';server_fingerprint='UNVERIFIED_DIAGNOSTIC';account_fingerprint='UNVERIFIED_DIAGNOSTIC';data_fingerprint='UNVERIFIED_DIAGNOSTIC';symbol_geometry=[ordered]@{digits=5;point=0.00001;pip_size=0.0001};include_closure_sha256=TextSha ''}
  $receipt=[ordered]@{schema_version='alphafactory_execution_receipt.v1';hypothesis_id='HYP-VRAS-EURUSD-M5-007';registry_row_sha256=TextSha $registryLine;task_packet_sha256=FileSha $taskPath;git_commit=$gitCommit;git_status_sha256=$gitStatusSha;binding=$binding;evidence=$evidence;generated_at_utc=(Get-Date).ToUniversalTime().ToString('o')}
  WriteJson $receipt $receiptPath
  $results+=[ordered]@{arm=$arm.name;task_packet=$taskPath;task_sha256=FileSha $taskPath;receipt=$receiptPath;receipt_sha256=FileSha $receiptPath;overrides=$overrides}
}
$results|ConvertTo-Json -Depth 6

