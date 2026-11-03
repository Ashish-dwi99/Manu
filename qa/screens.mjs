import { chromium } from '../apps/web/node_modules/playwright/index.mjs';
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const output=process.env.MANU_SHOTS || path.join(root,'qa','screenshots');
mkdirSync(output,{recursive:true});
const base='http://127.0.0.1:8790';
try { await fetch(base+'/api/cases'); throw new Error('Port 8790 is already in use; stop the existing demo before UI tests.'); } catch(e) { if(e.message.includes('already in use')) throw e; }
const server=spawn('uv',['run','manu','serve','--demo'],{cwd:root,stdio:'ignore'});
let browser;
try {
 for(let i=0;i<100;i++){try{if((await fetch(base+'/api/cases')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({channel:'chrome',args:['--no-sandbox']});
 const data=await (await fetch(base+'/api/cases')).json();
 const imran=data.cases.find(c=>c.title === 'State v. Imran Sheikh');const civil=data.cases.find(c=>!c.title.startsWith('State'));
 const errors=[];const checks=[];
 const p=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 p.on('pageerror',e=>errors.push(e.message));
 async function shot(name){if(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw new Error('Horizontal overflow: '+name);await p.screenshot({path:`${output}/${name}.png`});checks.push(name);}
 async function open(route){await p.goto(base+'/#'+route);if(route.startsWith('/c/')) await p.locator('.mn-case-title').waitFor(); else await p.locator('.mn-display').waitFor();await p.locator('.mn-faint.mn-pad').waitFor({state:'hidden'});}
 await open('/');await shot('01-today-desktop');
 await p.locator('input[aria-label="CNR or case to find"]').fill('nonsense');await shot('02-search-empty');
 await p.getByRole('button',{name:'Import by advocate name'}).click();await p.getByRole('textbox',{name:'Advocate name',exact:true}).fill('R. Mehta');await p.getByRole('button',{name:'Find cases',exact:true}).click();await p.locator('.mn-pick, .mn-empty').first().waitFor();await shot('03-import');
 await open('/week');await shot('04-week');await open('/changes');await shot('05-changes');await open('/attention');await shot('06-attention-desktop');
 const first=p.locator('.mn-block').filter({has:p.getByRole('heading',{name:'State v. Imran Sheikh',exact:true})}).locator('.mn-signal').filter({has:p.getByRole('button',{name:'Add step',exact:true})}).first();
 await first.locator('summary').click();await shot('07-evidence-expanded');
 await first.getByRole('button',{name:'Add step',exact:true}).click();await p.locator('.mn-step-actions').first().waitFor();await shot('08-step-added');
 await p.getByRole('button',{name:'Edit this step',exact:true}).first().click();await p.getByRole('textbox',{name:'Next step',exact:true}).fill('Review order and prepare hearing checklist');await shot('09-step-edit');await p.getByRole('button',{name:'Save',exact:true}).click();await p.locator('.mn-step-edit').waitFor({state:'hidden'});await Promise.all([p.waitForResponse(r=>r.url().includes('/obligations/') && r.request().method()==='POST'),p.locator('.mn-step-actions button[title="Done"]').first().click()]);await open('/c/'+imran.id);await p.reload();await p.locator('.mn-signal.step-done').first().waitFor();await shot('10-step-done');
 await open('/c/'+imran.id);await shot('11-case-desktop');await p.getByRole('button',{name:'Show sources',exact:true}).click();await p.locator('.mn-source-head').waitFor();await shot('12-order-source');
 for(const tab of ['Papers','Research','Dates','Timeline']){await p.getByRole('tab',{name:tab,exact:true}).click();await p.locator('.mn-panel .mn-faint.mn-pad').waitFor({state:'hidden'});await shot('13-panel-'+tab.toLowerCase());}
 await p.getByRole('tab',{name:'Research',exact:true}).click();await p.getByRole('textbox',{name:'Research',exact:true}).fill('bail');await p.getByRole('textbox',{name:'Research',exact:true}).press('Enter');await p.locator('.mn-hits, .mn-empty').first().waitFor();await shot('14-research-results');
 if(await p.locator('.mn-hit-title').count()){await p.locator('.mn-hit-title').first().click();await p.locator('.mn-paras').waitFor();await shot('15-judgment');}
 await p.getByRole('button',{name:'Close panel',exact:true}).click();
 for(const tab of ['Notes','Authorities','Deadline','Draft','Bail facts']){
  if(await p.getByRole('tab',{name:tab,exact:true}).count()) {await p.getByRole('tab',{name:tab,exact:true}).click();await p.locator('.mn-bench').scrollIntoViewIfNeeded();await shot('16-tool-'+tab.toLowerCase().replace(' ','-'));}
 }
 await p.getByRole('tab',{name:'Draft',exact:true}).click();
 const db=p.locator('.mn-draft-buttons button');if(await db.count()){await db.first().click();await p.locator('.mn-questions label').first().waitFor();await shot('17-application-draft');await p.getByRole('button',{name:'Close',exact:true}).click();}
 await p.getByRole('button',{name:'Draft a client update',exact:true}).click();await p.locator('textarea.mn-draft').waitFor();await p.waitForFunction(()=>document.querySelector('textarea.mn-draft')?.value.length>0);await shot('18-client-draft');await p.getByRole('button',{name:'Close',exact:true}).click();
 await open('/c/'+civil.id);await shot('19-civil-case');
 await p.getByRole('tab',{name:'Deadline',exact:true}).click();await p.locator('.mn-limitation').scrollIntoViewIfNeeded();const options=await p.locator('.mn-lim-form select').first().locator('option').allTextContents();await p.locator('.mn-lim-form select').first().selectOption({index:1});await p.locator('.mn-lim-result').waitFor();await shot('20-deadline-result');
 await p.setViewportSize({width:390,height:844});
 for(const [route,name] of [['/','21-today-phone'],['/attention','22-attention-phone'],['/week','23-week-phone'],['/changes','24-changes-phone'],['/c/'+imran.id,'25-case-phone']]){await open(route);await shot(name);checks.push([name,'overflow',await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth)]);}
 await p.getByRole('button',{name:'Show sources',exact:true}).click();await shot('26-source-phone');await p.getByRole('tab',{name:'Research',exact:true}).click();await shot('27-research-phone');await p.getByRole('button',{name:'Close panel',exact:true}).click();
 await p.getByRole('button',{name:'Draft a client update',exact:true}).click();await p.locator('textarea.mn-draft').waitFor();await p.waitForFunction(()=>document.querySelector('textarea.mn-draft')?.value.length>0);await shot('28-client-phone');
 await p.getByRole('button',{name:'Close',exact:true}).click();
 await p.getByRole('tab',{name:'Draft',exact:true}).click();await p.locator('.mn-draft-buttons button').first().click();await p.locator('.mn-questions label').first().waitFor();await shot('29-application-phone');await p.getByRole('button',{name:'Close',exact:true}).click();
 await p.setViewportSize({width:1440,height:1000});await open('/attention');await p.getByRole('button',{name:'Dark',exact:true}).click();await shot('30-attention-dark');
 await p.getByRole('button',{name:'Light',exact:true}).click();
 await p.route('**/api/attention?*',route=>route.fulfill({json:{count:0,entries:[],in_progress:[]}}));await p.reload();await p.getByText('No signals or open next steps.',{exact:true}).waitFor();await shot('31-attention-empty');await p.unroute('**/api/attention?*');
 await p.route('**/api/diary/day?*',route=>route.fulfill({status:503,json:{detail:'Test service unavailable'}}));await open('/');await p.getByRole('button',{name:'Try again',exact:true}).waitFor();await shot('32-load-error');await p.unroute('**/api/diary/day?*');await p.getByRole('button',{name:'Try again',exact:true}).click();await p.locator('.mn-boards').waitFor();checks.push('error-retry-recovers');
 // Complete screen inventory at both breakpoints, with real local fixtures only.
 for(const width of [1440,390]){
  await p.setViewportSize({width,height:width===390?844:1000});
  await open('/');await p.getByRole('button',{name:'Draft cause list',exact:true}).click();await p.waitForFunction(()=>document.querySelector('textarea.mn-draft')?.value.length>0);await shot(`matrix-${width}-cause-list`);await p.getByRole('button',{name:'Close',exact:true}).click();
  await p.getByRole('button',{name:'Import by advocate name',exact:true}).click();await p.getByRole('textbox',{name:'Advocate name',exact:true}).fill('not-a-real-advocate');await p.getByRole('button',{name:'Find cases',exact:true}).click();await p.locator('.mn-empty').waitFor();await shot(`matrix-${width}-import-empty`);
  await open('/c/'+imran.id);
  for(const tab of ['Notes','Authorities','Deadline','Draft','Bail facts']){
   await p.getByRole('tab',{name:tab,exact:true}).click();await p.locator('.mn-bench').scrollIntoViewIfNeeded();await shot(`matrix-${width}-tool-${tab.toLowerCase().replace(' ','-')}`);
  }
  await p.getByRole('button',{name:'Show sources',exact:true}).click();
  for(const tab of ['Source','Papers','Research','Dates','Timeline']){await p.getByRole('tab',{name:tab,exact:true}).click();await p.locator('.mn-panel .mn-faint.mn-pad').waitFor({state:'hidden'});await shot(`matrix-${width}-panel-${tab.toLowerCase()}`);}
  await p.getByRole('tab',{name:'Research',exact:true}).click();await p.locator('.mn-check summary').click();await p.locator('.mn-check textarea').fill('(2020) 5 SCC 1');await p.locator('.mn-check button').click();await p.locator('.mn-checks, .mn-check .mn-faint').first().waitFor();await shot(`matrix-${width}-citation-check`);
  await p.getByRole('button',{name:'Close panel',exact:true}).click();
  await p.getByRole('tab',{name:'Draft',exact:true}).click();await p.locator('.mn-draft-buttons button').nth(1).click();await p.locator('.mn-questions label').first().waitFor();await shot(`matrix-${width}-bail-draft`);await p.getByRole('button',{name:'Close',exact:true}).click();
  await p.getByRole('textbox',{name:'Ask about this case',exact:true}).fill('written synopsis');await p.getByRole('button',{name:'Ask',exact:true}).click();await p.locator('.mn-turn .mn-offline, .mn-turn .mn-answer').first().waitFor();await p.locator('.mn-thread').scrollIntoViewIfNeeded();await shot(`matrix-${width}-case-reader`);
  await p.route('**/api/diary/changes?*',r=>r.fulfill({json:{events:[]}}));await open('/changes');await p.reload();await p.getByText('No changes recorded yet.',{exact:true}).waitFor();await shot(`matrix-${width}-changes-empty`);await p.unroute('**/api/diary/changes?*');
  await p.route('**/api/diary/upcoming?*',r=>r.fulfill({json:{items:[]}}));await open('/week');await p.reload();await p.getByText('Nothing listed or due this week.',{exact:true}).waitFor();await shot(`matrix-${width}-week-empty`);await p.unroute('**/api/diary/upcoming?*');
 }
 // Mutation and source-detail paths use only fictional demo records.
 for(const width of [1440,390]) {
  await p.setViewportSize({width,height:width===390?844:1000});await open('/');
  await p.getByRole('button',{name:'Import by advocate name',exact:true}).click();await p.getByRole('textbox',{name:'Advocate name',exact:true}).fill('R. Mehta');await p.getByRole('button',{name:'Find cases',exact:true}).click();await p.locator('.mn-pick').first().waitFor();await shot(`detail-${width}-import-results`);
  const follow=p.getByRole('button',{name:/^Follow [1-9]/});if(await follow.count()){await follow.click();await p.getByRole('heading',{name:'Imported',exact:true}).waitFor();await shot(`detail-${width}-import-confirmation`);}
  const liveCases=await(await fetch(base+'/api/cases')).json();imran.id=liveCases.cases.find(c=>c.title==='State v. Imran Sheikh').id;await open('/c/'+imran.id);await p.reload();await p.locator('.mn-bench').waitFor();await p.getByRole('tab',{name:'Notes',exact:true}).click();await p.getByRole('textbox',{name:'New note',exact:true}).fill('Fictional QA note: check the missing order.');await p.getByRole('button',{name:'Save note',exact:true}).click();await p.locator('.mn-notes').waitFor();await p.locator('.mn-notes').scrollIntoViewIfNeeded();await shot(`detail-${width}-note-saved`);
  await p.getByRole('button',{name:'Show sources',exact:true}).click();await p.getByRole('tab',{name:'Papers',exact:true}).click();
  await p.locator('input[type=file]').setInputFiles({name:'fictional-review.txt',mimeType:'text/plain',buffer:Buffer.from('Fictional QA record only. The hearing checklist was reviewed. No real case data.')});await p.getByRole('button',{name:/fictional-review.txt/}).first().waitFor();await shot(`detail-${width}-papers-added`);
  await p.getByRole('button',{name:/fictional-review.txt/}).first().click();await p.locator('.mn-doc-text').filter({hasText:'Fictional QA record only'}).waitFor();await shot(`detail-${width}-paper-page`);
  await p.getByRole('button',{name:'Close panel',exact:true}).click();
  await p.getByRole('tab',{name:'Draft',exact:true}).click();await p.locator('.mn-draft-buttons button').first().click();await p.locator('.mn-questions label').first().waitFor();
  await p.locator('.mn-questions label').filter({hasText:'On whose behalf'}).locator('input').fill('accused');await p.locator('.mn-questions textarea').first().fill('Fictional QA: counsel is unavailable.');await p.getByText('Ready for review.',{exact:true}).waitFor();await shot(`detail-${width}-application-ready`);await p.getByRole('button',{name:'Close',exact:true}).click();
  await p.route('**/api/attention?*',async route=>{await new Promise(r=>setTimeout(r,1000));await route.fulfill({json:{count:0,entries:[],in_progress:[]}})});await p.goto(base+'/#/attention');await p.reload();await p.getByText('Loading…',{exact:true}).first().waitFor();await shot(`detail-${width}-loading`);await p.getByText('No signals or open next steps.',{exact:true}).waitFor();await p.unroute('**/api/attention?*');
  await p.route('**/api/diary/changes?*',r=>r.fulfill({status:503,json:{detail:'Simulated failure'}}));await p.goto(base+'/#/changes');await p.reload();await p.getByRole('button',{name:'Try again',exact:true}).waitFor();await shot(`detail-${width}-error`);await p.unroute('**/api/diary/changes?*');
 }
 if(errors.length) throw new Error(errors.join(' | '));
 await p.setViewportSize({width:390,height:844});await open('/c/'+imran.id);await p.getByRole('button',{name:'Show sources',exact:true}).click();await p.locator('.mn-panel .mn-faint.mn-pad').waitFor({state:'hidden'});await shot('final-source-phone');if(!(await p.getByRole('button',{name:'Close panel',exact:true}).isVisible())) throw new Error('Panel close hidden');
 console.log(JSON.stringify({checks,errors}));writeFileSync(path.join(output,'checks.json'),JSON.stringify({checks,errors},null,2));
}finally{await browser?.close();server.kill('SIGTERM');}
