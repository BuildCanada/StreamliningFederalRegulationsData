# Data for Streamlining Federal Regulations

## Purpose
This repo aim to act as the centralized data collection point for streamlining federal regulations, to be used for various data processing and prompting. Exact structure is still under construction. The codebase is expected to be in a separate repo; link to be added *here*

This README will be updated as the project evolves.

## Structure
Work in progres.. 

- The data in `/JusticeLawWebsite/raw` are in XML format as-is and is expected to requires post-processing prior to use (e.g. remove unnecessary metadata)  
    - Data in `/JusticeLawWebsite/formatted` has been formated with `xmllint` to make it more human-readable.
- The data in `/StatuteRepeal/` are in HTML and PHP format and contains data published under the Statutes Repeal Act. Source: <https://laws-lois.justice.gc.ca/eng/Reports/>
- The data in '/GazettePartI/Index' are in HTML/PDF format as-is and contains the quaterly index files only. Part I notices related to *Repeals* can be found in `/StatusRepeal/` 

To be added:  
- Data from [Open Government](https://open.canada.ca/en) as required.   


## Head Document
Google Docs: [Streamlining Federal Regulations](https://docs.google.com/document/d/1bK7jQEfs73cw1JXyj67MIymM80KJUvwWhJz5gr8jqNQ/edit?tab=t.0#heading=h.34b2u2ezzq7m)

## Contribution
Join us on [Discord](https://discord.com/channels/1384033183112237208/1407386107737407631)

## License

 **Root** and most folders are reproduced under the  **Open Government Licence – Canada (Version 2.0)**.   
Full text: <https://open.canada.ca/en/open-government-licence-canada>

**Files under `/JusticeLawWebsite/`** are reproduced under the **Reproduction of Federal Law Order**.    
Full text: <https://laws-lois.justice.gc.ca/eng/regulations/SI-97-5/page-1.html>

**Other** folders may include additional LICENSE.md files where specific terms apply.    
