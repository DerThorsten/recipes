print('Loading flexclust package')
library(flexclust)
print('... flexclust package loaded successfully')

test_1 <- function() {
    data(Nclus)
    cl <- cclust(Nclus, k=4, simple=FALSE, save.data=TRUE)
    plot(cl)
}

test_2 <- function() {
    data(auto)
    summary(auto)
}

test_3 <- function() {
      cl <- cclust(iris[,-5], k=3)
      barplot(cl)
      barplot(cl, bycluster=FALSE)

      ## plot the maximum instead of mean value per cluster:
      barplot(cl, bycluster=FALSE, data=iris[,-5],
              FUN=function(x) apply(x,2,max))

      ## use lattice for plotting:
      barchart(cl)
      ## automatic abbreviation of labels
      barchart(cl, scales=list(abbreviate=TRUE))
      ## origin of bars at zero
      barchart(cl, scales=list(abbreviate=TRUE), origin=0)

      ## Use manual labels. Note that the flexclust barchart orders bars
      ## from top to bottom (the default does it the other way round), hence
      ## we have to rev() the labels:
      LAB <- c("SL", "SW", "PL", "PW")
      barchart(cl, scales=list(y=list(labels=rev(LAB))), origin=0)

      ## deviation of each cluster center from the population means
      barchart(cl, origin=rev(cl@xcent), mlcol=NULL)

      ## use shading to highlight large deviations from population mean
      barchart(cl, shade=TRUE)

      ## use smaller deviation limit than default and add a legend
      barchart(cl, shade=TRUE, diff=0.2, legend=TRUE)
}

test_4 <- function() {
    data(iris)
    bc1 <- bclust(iris[,1:4], 3, base.k=5)
    plot(bc1)

    table(clusters(bc1, k=3))
    parameters(bc1, k=3)
}

test_5 <- function() {
    p02 <- bundestag(2002)
    pairs(p02)
    p05 <- bundestag(2005)
    pairs(p05)
    p09 <- bundestag(2009)
    pairs(p09)

    state <- bundestag(2002, state=TRUE)
    table(state)

    start.with.b <- bundestag(2002, state="^B")
    table(start.with.b)

    pairs(p09, col=2-(state=="Bayern"))
}

test_6 <- function() {
      set.seed(1)
      cl <- cclust(iris[,-5], k=3, save.data=TRUE)
      bwplot(cl)
      bwplot(cl, byvar=TRUE)

      ## fill only boxes with color which do not contain the overall median
      ## (grey dot of background box)
      bwplot(cl, shade=TRUE)

      ## fill only boxes with color which do not overlap with the box of the
      ## complete sample (grey background box)
      bwplot(cl, shadefun="boxOverlap")
}

test_7 <- function() {
    ## a 2-dimensional example
    x <- rbind(matrix(rnorm(100, sd=0.3), ncol=2),
               matrix(rnorm(100, mean=1, sd=0.3), ncol=2))
    cl <- cclust(x,2)
    plot(x, col=predict(cl))
    points(cl@centers, pch="x", cex=2, col=3) 

    ## a 3-dimensional example 
    x <- rbind(matrix(rnorm(150, sd=0.3), ncol=3),
               matrix(rnorm(150, mean=2, sd=0.3), ncol=3),
               matrix(rnorm(150, mean=4, sd=0.3), ncol=3))
    cl <- cclust(x, 6, method="neuralgas", save.data=TRUE)
    pairs(x, col=predict(cl))
    plot(cl)
}

test_8 <- function() {
    example(Nclus)

    clusterSim(cl)
    clusterSim(cl, symmetric=TRUE)

    ## should have similar structure but will be numerically different:
    clusterSim(cl, symmetric=TRUE, data=Nclus[sample(1:550, 200),])

    ## different concept of cluster similarity
    clusterSim(cl, method="centers")
}


print("Running test_1")
test_1()

print("Running test_2")
test_2()

print("Running test_3")
test_3()

print("Running test_4")
test_4()

print("Running test_5")
test_5()

print("Running test_6")
test_6()

print("Running test_7")
test_7()

print("Running test_8")
test_8()

