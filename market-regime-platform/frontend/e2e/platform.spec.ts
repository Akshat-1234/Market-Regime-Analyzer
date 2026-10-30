import { test, expect, type Page } from '@playwright/test';

const REFERENCE='run_20261030_081436_12ea5b';
const SENSITIVITY='run_20261030_080824_12346d';
async function loadRun(page:Page,path:string){
  await page.goto(path);
  const selector=page.getByLabel('Research run');
  await expect(selector.locator(`option[value="${REFERENCE}"]`)).toHaveCount(1);
  await selector.selectOption(REFERENCE);
}

test('overview shows real results and exactly five primary sections',async({page,request})=>{
  const o=await (await request.get(`/api/runs/${REFERENCE}/overview`)).json();
  await loadRun(page,'/');
  await expect(page.getByRole('heading',{name:'Research overview'})).toBeVisible();
  await expect(page.getByText('INTERVAL INCLUDES ZERO',{exact:true})).toBeVisible();
  await expect(page.getByText('3,632 sessions')).toBeVisible();
  await expect(page.getByText('17.2%').first()).toBeVisible();
  await expect(page.getByRole('navigation',{name:'Primary navigation'}).getByRole('link')).toHaveCount(5);
  expect(o.metadata.last_return_date).toBe('2026-10-22');
});

test('range, strategy selection, attribution control and CSV downloads work',async({page})=>{
  await loadRun(page,'/strategies');
  await expect(page.getByRole('heading',{name:'Strategy compare'})).toBeVisible();
  const momentum=page.getByRole('button',{name:'Momentum 20',exact:true});await momentum.click();
  await expect(momentum).toHaveAttribute('aria-pressed','true');
  await expect(page.getByRole('cell',{name:'Momentum 20'})).toBeVisible();
  await page.getByRole('button',{name:'1Y',exact:true}).click();
  await expect(page.getByLabel('Start date')).toHaveValue('2025-10-22');
  await page.getByLabel('Attribution control').selectOption('Past-only block shuffled');
  await expect(page.getByText('BLOCK SHUFFLED',{exact:true})).toBeVisible();
  const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('link',{name:'Summary CSV'}).click()]);
  expect(download.suggestedFilename()).toContain('attribution.csv');
});

test('regime model dropdown updates state labels without relabeling two-state model',async({page})=>{
  await loadRun(page,'/regimes');
  await expect(page.getByRole('heading',{name:'Regime explorer'})).toBeVisible();
  await page.getByLabel('HMM model').selectOption('rv_2');
  await expect(page.getByText('STATE 1 · HIGHER VOL',{exact:true})).toBeVisible();
  await expect(page.getByText(/Select rvd_3 to view/)).toBeVisible();
});

test('validation exposes pending holdout and run-provenance differences',async({page})=>{
  await loadRun(page,'/validation');
  await expect(page.getByRole('heading',{name:'Validation',exact:true})).toBeVisible();
  await expect(page.getByText('PROSPECTIVE HOLDOUT',{exact:true})).toBeVisible();
  await expect(page.getByText('CHECK DIFFERENCES')).toBeVisible();
  await expect(page.getByText(/Control lookbacks differ/)).toBeVisible();
  await page.getByLabel('Validation strategy').selectOption('Buy & Hold');
  await expect(page.getByLabel('Validation strategy')).toHaveValue('Buy & Hold');
  await expect(page.locator('table').first().locator('tbody tr').first().locator('td').nth(5)).toHaveText('27.6%');
});

test('data quality filters, table export and run dialog are interactive',async({page})=>{
  await loadRun(page,'/data-quality');await expect(page.getByRole('heading',{name:'Data quality'})).toBeVisible();
  await page.getByLabel('Quality flag filter').selectOption('Extreme close return');
  await expect(page.getByText('43 rows',{exact:true})).toBeVisible();
  const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Export filtered CSV'}).first().click()]);
  expect(download.suggestedFilename()).toBe('quality_flags_filtered.csv');
  await page.getByRole('button',{name:'New run'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByLabel('Execution timing').selectOption('0');
  await expect(page.getByText('Same-close execution is an optimistic sensitivity case, not next-open execution.')).toBeVisible();
  await page.getByRole('button',{name:'Close dialog'}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('run selector switches to retained full-history sensitivity',async({page})=>{
  await loadRun(page,'/strategies');const selector=page.getByLabel('Research run');
  const values=await selector.locator('option').evaluateAll(nodes=>nodes.map((n:any)=>n.value));
  expect(values.length).toBeGreaterThanOrEqual(2);await selector.selectOption(SENSITIVITY);
  await expect(page.getByText(/Full prior history; seed/)).toBeVisible();
});

test('mobile navigation remains usable',async({page})=>{
  await page.setViewportSize({width:390,height:844});await loadRun(page,'/');
  await expect(page.getByRole('heading',{name:'Research overview'})).toBeVisible();
  await page.getByRole('link',{name:'Data Quality',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Data quality'})).toBeVisible();
  const dimensions=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width+1);
});
