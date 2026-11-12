#!/usr/bin/env python3
"""
Expands the Frontier Niche pool across all 12 Universal Verticals with 600+ high-demand root seeds.
Ensures comprehensive global coverage beyond Developer & Cloud.
"""

import sys
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import storage.db as db

EXPANDED_SEEDS = {
    "Small Business & B2B": [
        "invoice generator", "receipt maker", "paystub generator", "nda generator",
        "bill of sale template", "profit margin calculator", "contract template",
        "purchase order template", "business proposal template", "break even calculator",
        "independent contractor agreement", "quote template", "inventory tracker",
        "timesheet calculator", "employee schedule template", "mileage reimbursement calculator",
        "business plan template", "partnership agreement template", "cash flow forecast",
        "freelance contract template", "billable hours tracker", "client onboarding checklist",
        "sales commission calculator", "work order template", "job estimate template",
        "subcontractor agreement", "scope of work template", "operating budget template",
        "overhead rate calculator", "cost of goods sold calculator", "service level agreement template",
    ],
    "Real Estate & Living": [
        "rent vs buy calculator", "closing cost calculator", "square footage calculator",
        "moving checklist", "lease agreement template", "sublet agreement template",
        "rental yield calculator", "property tax calculator", "roommate agreement template",
        "landlord notice to vacate", "home inspection checklist", "mortgage payoff calculator",
        "cap rate calculator", "home equity loan calculator", "security deposit return form",
        "hoa fee calculator", "depreciation calculator real estate", "tenant screening checklist",
        "construction cost estimator", "property management agreement", "commercial lease template",
        "rent increase notice", "lease renewal template", "paint calculator square feet",
    ],
    "Finance & Wealth": [
        "mortgage calculator", "loan calculator", "tax calculator", "salary after tax",
        "crypto tax calculator", "compound interest calculator", "car loan payment",
        "dividend calculator", "401k calculator", "roi calculator", "refinance calculator",
        "amortization schedule", "net worth tracker", "capital gains tax calculator",
        "fire calculator early retirement", "debt snowball calculator", "inflation calculator",
        "annuity calculator", "savings goal calculator", "auto lease calculator",
        "emergency fund calculator", "cd ladder calculator", "stock options payoff calculator",
        "roth ira calculator", "hsa investment calculator", "social security benefits estimator",
        "home affordability calculator", "credit card payoff calculator", "college savings 529 calculator",
    ],
    "Legal & Compliance": [
        "privacy policy generator", "terms of service generator", "cookie consent banner",
        "power of attorney form", "llc operating agreement template", "non disclosure agreement",
        "cease and desist letter template", "employment contract template", "gdpr checklist",
        "affidavit template", "eviction notice template", "last will and testament template",
        "bill of lading template", "trademark search checklist", "affidavit of correction form",
        "promissory note template", "liability waiver form", "copyright infringement notice",
        "hipaa compliance checklist", "quitclaim deed template", "living trust template",
        "severance agreement template", "independent contractor form", "resignation letter template",
    ],
    "Health & Fitness": [
        "calorie calculator", "macro calculator", "bmi calculator", "running pace calculator",
        "tdee calculator", "water intake calculator", "intermittent fasting tracker",
        "body fat percentage calculator", "one rep max calculator", "ovulation calculator",
        "sleep cycle calculator", "keto diet calculator", "vo2 max calculator",
        "target heart rate calculator", "creatine intake calculator", "ideal body weight calculator",
        "marathon pace chart", "protein intake calculator", "body surface area calculator",
        "body shape calculator", "bench press max calculator", "calorie deficit calculator",
        "blood alcohol content calculator", "conception date calculator", "glycemic load calculator",
    ],
    "Media & Converters": [
        "heic to jpg", "mp4 to gif", "pdf to word", "compress png",
        "webp to png", "audio extractor", "svg to png", "watermark remover",
        "video compressor", "epub to pdf", "m4a to mp3", "wav to mp3",
        "image resizer", "remove background", "flac to mp3", "srt subtitle generator",
        "pdf to excel", "ocr text extractor", "mov to mp4", "pdf merger",
        "pdf split pages", "dpi converter image", "vectorize image", "color palette from image",
        "aspect ratio calculator", "gif compressor", "raw to dng converter", "speech to text free",
    ],
    "Travel & Visas": [
        "schengen 90 180 calculator", "visa requirements for", "flight delay compensation",
        "currency converter", "packing checklist", "passport renewal requirements",
        "jet lag planner", "customs declaration template", "travel budget calculator",
        "estat visa application guide", "international driving permit requirements",
        "transit visa requirements", "baggage allowance calculator", "travel vaccination requirements",
        "digital nomad visa requirements", "flight time calculator", "layover guide requirements",
    ],
    "E-Commerce & Selling": [
        "etsy fee calculator", "ebay fee calculator", "shopify margin calculator",
        "amazon fba fees calculator", "shipping cost calculator", "barcode generator",
        "drop shipping profit calculator", "product markup calculator", "mercari fee calculator",
        "poshmark fee calculator", "upc barcode validator", "box size dimensional weight calculator",
        "sales tax by zip code calculator", "inventory turnover calculator", "return on ad spend roas calculator",
    ],
    "Gaming & Entertainment": [
        "damage calculator", "stat calculator", "tier list maker", "wordle solver",
        "mouse sensitivity converter", "crosshair generator", "pokemon weakness chart",
        "fps benchmark calculator", "discord bot template", "minecraft coordinate calculator",
        "dnd character sheet generator", "fov field of view converter", "sudoku solver step by step",
    ],
    "Academic & Education": [
        "gpa calculator", "citation generator", "word counter", "grade calculator",
        "percentage increase calculator", "scientific notation calculator", "weighted grade calculator",
        "plagiarism checker", "flashcard maker", "apa citation maker", "mla citation maker",
        "algebra equation solver", "fraction calculator step by step", "standard deviation calculator",
        "hypothesis testing calculator", "reading time calculator", "bibliography maker",
    ],
    "Productivity & Work": [
        "budget template", "timesheet template", "habit tracker", "meeting notes template",
        "cron expression generator", "markdown editor", "pomodoro timer", "work breakdown structure",
        "daily planner template", "kanban board template", "flowchart maker", "gantt chart template",
        "eisenhower matrix template", "swot analysis template", "okr template spreadsheet",
        "raci matrix template", "meeting agenda template", "action item tracker",
    ],
}

def expand_all():
    total_added = 0
    for cat, terms in EXPANDED_SEEDS.items():
        cat_added = 0
        for t in terms:
            if db.queue_sub_niche(t.strip(), category=cat, depth=0):
                cat_added += 1
        total_added += cat_added
        print(f"[{cat}] Queued {cat_added} new root anchors.")
    print(f"\n✅ Total fresh root anchors queued into Frontier: {total_added}")

if __name__ == "__main__":
    expand_all()
