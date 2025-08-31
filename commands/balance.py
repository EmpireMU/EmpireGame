"""
Balance Analysis Command

This is a temporary administrative tool for analyzing character balance.
It can be safely removed once game balancing is complete.

Usage: balance
"""

from evennia import Command
from evennia import CmdSet


class CmdBalance(Command):
    """
    Analyze character balance across all finished characters.
    
    Usage:
        balance
        
    This administrative tool provides statistical analysis of all finished
    characters to identify potential balance issues. It shows:
    
    - Attribute and skill distributions
    - Power rankings
    - Outlier detection
    - Additional traits analysis
    
    This is a temporary tool that can be safely removed once game
    balancing is complete.
    
    Staff only.
    """
    
    key = "balance"
    locks = "cmd:perm(Builder)"
    help_category = "Admin"
    
    def func(self):
        """Execute the balance analysis."""
        from typeclasses.characters import Character, STATUS_AVAILABLE, STATUS_ACTIVE, STATUS_GONE
        from utils.trait_definitions import ATTRIBUTES, SKILLS
        
        # Get all finished characters
        finished_statuses = [STATUS_AVAILABLE, STATUS_ACTIVE, STATUS_GONE]
        all_chars = Character.objects.all()
        finished_chars = []
        
        for char in all_chars:
            # Skip staff accounts
            if char.account and char.account.check_permstring("Builder"):
                continue
                
            # Only include finished characters with character sheet data
            if (char.db.status in finished_statuses and 
                hasattr(char, 'character_attributes')):
                finished_chars.append(char)
        
        if not finished_chars:
            self.msg("No finished characters found for analysis.")
            return
        
        # Collect trait data
        char_data = []
        for char in finished_chars:
            data = {'name': char.name}
            
            # Collect attributes
            attr_total = 0
            attr_count = 0
            for attr_def in ATTRIBUTES:
                trait = char.character_attributes.get(attr_def.key)
                if trait:
                    value = int(trait.value)
                    data[f"attr_{attr_def.key}"] = value
                    attr_total += value
                    attr_count += 1
                else:
                    data[f"attr_{attr_def.key}"] = 6  # default
                    attr_total += 6
                    attr_count += 1
                    
            # Collect skills
            skill_total = 0
            skill_count = 0
            skills_above_default = 0
            for skill_def in SKILLS:
                trait = char.skills.get(skill_def.key)
                if trait:
                    value = int(trait.value)
                    data[f"skill_{skill_def.key}"] = value
                    skill_total += value
                    skill_count += 1
                    if value > 4:  # above default
                        skills_above_default += 1
                else:
                    data[f"skill_{skill_def.key}"] = 4  # default
                    skill_total += 4
                    skill_count += 1
            
            # Calculate totals and averages
            data['attr_total'] = attr_total
            data['attr_average'] = attr_total / attr_count if attr_count > 0 else 0
            data['skill_total'] = skill_total
            data['skill_average'] = skill_total / skill_count if skill_count > 0 else 0
            data['skills_above_default'] = skills_above_default
            
            # Count additional traits
            data['signature_assets'] = len([k for k in char.signature_assets.all() if char.signature_assets.get(k)])
            data['powers'] = len([k for k in char.powers.all() if char.powers.get(k)])
            data['resources'] = len([k for k in char.char_resources.all() if char.char_resources.get(k)])
            
            char_data.append(data)
        
        # Calculate statistics
        output = []
        output.append("="*80)
        output.append(f"|wCHARACTER BALANCE ANALYSIS|n ({len(finished_chars)} characters)")
        output.append("="*80)
        
        # Attribute analysis
        attr_totals = [data['attr_total'] for data in char_data]
        attr_avg = sum(attr_totals) / len(attr_totals)
        attr_min = min(attr_totals)
        attr_max = max(attr_totals)
        
        output.append(f"\n|yAttribute Totals:|n")
        output.append(f"  Average: {attr_avg:.1f} (baseline: {6 * len(ATTRIBUTES)})")
        output.append(f"  Range: {attr_min} - {attr_max}")
        
        # Find outliers (more than 1 standard deviation from mean)
        attr_std = (sum((x - attr_avg) ** 2 for x in attr_totals) / len(attr_totals)) ** 0.5
        outliers = []
        for data in char_data:
            if abs(data['attr_total'] - attr_avg) > attr_std:
                outliers.append(f"{data['name']} ({data['attr_total']})")
        
        if outliers:
            output.append(f"  |rOutliers:|n {', '.join(outliers)}")
        
        # Skill analysis
        skill_totals = [data['skill_total'] for data in char_data]
        skill_avg = sum(skill_totals) / len(skill_totals)
        skill_min = min(skill_totals)
        skill_max = max(skill_totals)
        skills_trained = [data['skills_above_default'] for data in char_data]
        skills_trained_avg = sum(skills_trained) / len(skills_trained)
        
        output.append(f"\n|ySkill Analysis:|n")
        output.append(f"  Total points - Average: {skill_avg:.1f} (baseline: {4 * len(SKILLS)})")
        output.append(f"  Total points - Range: {skill_min} - {skill_max}")
        output.append(f"  Trained skills - Average: {skills_trained_avg:.1f} per character")
        
        # Find skill outliers
        skill_std = (sum((x - skill_avg) ** 2 for x in skill_totals) / len(skill_totals)) ** 0.5
        skill_outliers = []
        for data in char_data:
            if abs(data['skill_total'] - skill_avg) > skill_std:
                skill_outliers.append(f"{data['name']} ({data['skill_total']})")
        
        if skill_outliers:
            output.append(f"  |rOutliers:|n {', '.join(skill_outliers)}")
        
        # Additional traits analysis
        sig_assets = [data['signature_assets'] for data in char_data]
        powers = [data['powers'] for data in char_data]
        resources = [data['resources'] for data in char_data]
        
        if any(sig_assets) or any(powers) or any(resources):
            output.append(f"\n|yAdditional Traits:|n")
            if any(sig_assets):
                output.append(f"  Signature Assets - Average: {sum(sig_assets)/len(sig_assets):.1f}, Max: {max(sig_assets)}")
            if any(powers):
                output.append(f"  Powers - Average: {sum(powers)/len(powers):.1f}, Max: {max(powers)}")
            if any(resources):
                output.append(f"  Resources - Average: {sum(resources)/len(resources):.1f}, Max: {max(resources)}")
        
        # Character power ranking
        output.append(f"\n|yPower Rankings:|n")
        # Simple power score: attr_total + skill_total + extras
        power_scores = []
        for data in char_data:
            extras = data['signature_assets'] * 6 + data['powers'] * 8 + data['resources'] * 5  # weighted
            power_score = data['attr_total'] + data['skill_total'] + extras
            power_scores.append((data['name'], power_score, data['attr_total'], data['skill_total'], extras))
        
        power_scores.sort(key=lambda x: x[1], reverse=True)
        
        for i, (name, total, attrs, skills, extras) in enumerate(power_scores[:5]):
            output.append(f"  {i+1:2}. {name:<20} Total: {total:3} (Attr: {attrs}, Skill: {skills}, Extras: {extras})")
        
        if len(power_scores) > 5:
            output.append(f"     ... and {len(power_scores) - 5} more")
        
        # Balance warnings
        warnings = []
        power_avg = sum(score[1] for score in power_scores) / len(power_scores)
        power_std = (sum((score[1] - power_avg) ** 2 for score in power_scores) / len(power_scores)) ** 0.5
        
        for name, total, attrs, skills, extras in power_scores:
            if total > power_avg + (1.5 * power_std):
                warnings.append(f"|r{name}|n significantly above average")
            elif total < power_avg - (1.5 * power_std):
                warnings.append(f"|y{name}|n significantly below average")
        
        if warnings:
            output.append(f"\n|rBalance Warnings:|n")
            for warning in warnings:
                output.append(f"  • {warning}")
        else:
            output.append(f"\n|gNo major balance issues detected.|n")
        
        output.append("="*80)
        self.msg("\n".join(output))


class BalanceCmdSet(CmdSet):
    """
    Command set for the balance analysis tool.
    This is a temporary admin tool and can be safely removed.
    """
    
    def at_cmdset_creation(self):
        """Populate the cmdset."""
        self.add(CmdBalance())
