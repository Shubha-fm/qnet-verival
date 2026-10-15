------------------------- MODULE ResourcePool -------------------------
EXTENDS Integers, TLC
CONSTANTS N, C, Mode, L, D
VARIABLES w, p, d, a, free, clock, stale
vars == <<w,p,d,a,free,clock,stale>>
Init == /\ w=N /\ p=0 /\ d=0 /\ a=0 /\ free=C
        /\ clock=0 /\ stale=FALSE
Terminal == w+p=0
Fresh == clock<L
Within == clock<D
Advance == clock'=IF clock<D THEN clock+1 ELSE D
Tick == /\ ~Terminal /\ Within /\ Advance
        /\ UNCHANGED <<w,p,d,a,free,stale>>
Atomic == /\ ~Terminal /\ Within /\ Fresh /\ w>0 /\ free>0
          /\ Mode="atomic" /\ w'=w-1 /\ d'=d+1 /\ free'=free-1
          /\ Advance /\ UNCHANGED <<p,a,stale>>
Prepare == /\ ~Terminal /\ Within /\ Fresh /\ w>0 /\ free>0
           /\ Mode # "atomic" /\ w'=w-1 /\ p'=p+1
           /\ free'=IF Mode="reserved" THEN free-1 ELSE free
           /\ Advance /\ UNCHANGED <<d,a,stale>>
Commit == /\ ~Terminal /\ Within /\ p>0
          /\ (Mode="split" \/ Fresh) /\ p'=p-1 /\ d'=d+1
          /\ free'=IF Mode="split" THEN free-1 ELSE free
          /\ stale'=(stale \/ ~Fresh) /\ Advance /\ UNCHANGED <<w,a>>
AbortWaiting == /\ ~Terminal /\ w>0
                /\ (~Fresh \/ ~Within \/ free<=0)
                /\ w'=w-1 /\ a'=a+1 /\ Advance
                /\ UNCHANGED <<p,d,free,stale>>
AbortPrepared == /\ ~Terminal /\ p>0
                 /\ (~Fresh \/ ~Within \/ (Mode="split" /\ free<=0))
                 /\ p'=p-1 /\ a'=a+1
                 /\ free'=IF Mode="reserved" /\ Fresh THEN free+1 ELSE free
                 /\ Advance /\ UNCHANGED <<w,d,stale>>
Next == Tick \/ Atomic \/ Prepare \/ Commit \/ AbortWaiting \/ AbortPrepared
Capacity == free>=0 /\ d<=C
FreshCommit == ~stale
Accounting == w+p+d+a=N /\ w>=0 /\ p>=0 /\ d>=0 /\ a>=0
              /\ (Mode # "reserved" \/ free+p+d<=C)
Safety == Capacity /\ FreshCommit /\ Accounting
=============================================================================
