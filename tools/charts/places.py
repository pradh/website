import csv
import datacommons as dc


all_places = set()
result = []

def process(parent, child_type):
  all_places.add(parent)
  children = sorted(dc.get_places_in([parent], child_type)[parent])

  if parent == 'Earth' and child_type == 'Country':
    cl = ['country/USA', 'country/CHN', 'country/IND',
          'country/AUS', 'country/FRA', 'country/BRA']
  else:
    cl = children[:5]

  row = {
    'Parent': parent,
    'ChildType': child_type,
    'Children': ','.join(cl),
  }
  all_places.update(cl)

  result.append(row)

  # Recurse into Continents and States, but not Country or County.
  grand_child_type = ''
  if child_type == 'Continent':
    grand_child_type = 'Country'
  elif child_type == 'State':
    grand_child_type = 'County'
  elif child_type == 'County':
    grand_child_type = 'City'
    # Have few counties per state.
    children = children[-1:]
  if not grand_child_type:
    return

  all_places.update(children)
  for c in children:
    process(c, grand_child_type)


def main():
  process('Earth', 'Continent')
  process('Earth', 'Country')
  process('country/USA', 'State')
  with open('places.csv', 'w') as fp:
    csvw = csv.DictWriter(fp, fieldnames=['Parent', 'ChildType', 'Children'])
    csvw.writeheader()
    csvw.writerows(result)
  with open('all_places.csv', 'w') as fp:
    fp.write('\n'.join(sorted(list(all_places))))


if __name__ == "__main__":
  main()
