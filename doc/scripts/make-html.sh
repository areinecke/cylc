#!/bin/bash

#C: THIS FILE IS PART OF THE CYLC SUITE ENGINE.
#C: Copyright (C) 2008-2014 Hilary Oliver, NIWA
#C: 
#C: This program is free software: you can redistribute it and/or modify
#C: it under the terms of the GNU General Public License as published by
#C: the Free Software Foundation, either version 3 of the License, or
#C: (at your option) any later version.
#C:
#C: This program is distributed in the hope that it will be useful,
#C: but WITHOUT ANY WARRANTY; without even the implied warranty of
#C: MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#C: GNU General Public License for more details.
#C:
#C: You should have received a copy of the GNU General Public License
#C: along with this program.  If not, see <http://www.gnu.org/licenses/>.

set -e

CYLC=$(dirname $0)/../../bin/cylc

function usage {
    echo "USAGE make-html.sh [multi|single]"
}

if [[ $# != 1 ]]; then
    usage
    exit 1
fi

TYPE=$1
if [[ $TYPE != multi ]] && [[ $TYPE != single ]]; then
    usage
    exit 1
fi

DEST=html/$TYPE
rm -rf $DEST; mkdir -p $DEST

$CYLC -v > cylc-version.txt

cp -r *.tex cug-html.cfg cylc-version.txt titlepic.sty $DEST
cd $DEST
ls *.tex | xargs -n 1 perl -pi -e 's@graphics/png/orig@../../graphics/png/scaled@g'
ls *.tex | xargs -n 1 perl -pi -e 's@\.\./examples/@../../../examples/@g'
ls *.tex | xargs -n 1 perl -pi -e 's@\.\./conf/@../../../conf/@g'
perl -pi -e 's@categories/@../../categories/@g' commands.tex
perl -pi -e 's@commands/@../../commands/@g' commands.tex
perl -pi -e 's@cylc.txt@../../cylc.txt@g' commands.tex
perl -pi -e 's@\.\./README@../../../README@g' cug.tex
perl -pi -e 's@\.\./INSTALL@../../../INSTALL@g' cug.tex

# NOTE the 5th argument '-halt-on-error' is passed to the latex
# compiler, but htlatex does not return error status if latex aborts.
# This is ok for cylc test purposes as we run pdflatex before htlatex.
if [[ $TYPE == multi ]]; then
    htlatex cug-html.tex "cug-html.cfg,html,fn-in,2,next" "" "" "-halt-on-error"
else
    htlatex cug-html.tex "cug-html.cfg,html,1,fn-in" "" "" "-halt-on-error"
fi

